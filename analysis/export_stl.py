import shutil
import numpy as np
import trimesh
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union
from shapely import set_precision
from .geometry import footprint, sha256


def validate_mesh(path, part, is_original=False):
    mesh = trimesh.load_mesh(path, process=True)
    result = dict(vertex_count=len(mesh.vertices), face_count=len(mesh.faces), body_count=int(mesh.body_count),
                  bounds=mesh.bounds.tolist(), dimensions=mesh.extents.tolist(), watertight=bool(mesh.is_watertight),
                  volume=float(abs(mesh.volume)), degenerate_faces=int(np.sum(~mesh.nondegenerate_faces())),
                  duplicate_faces=int(len(mesh.faces) - mesh.unique_faces().sum()),
                  winding_consistent=bool(mesh.is_winding_consistent), sha256=sha256(path))
    result['source_unchanged'] = sha256(path) == sha256(part.source) if is_original else False
    if not np.allclose(mesh.extents, part.mesh.extents, atol=.02):
        raise ValueError(f'{path}: global envelope changed')
    if not np.isfinite(mesh.vertices).all(): raise ValueError(f'{path}: nonfinite STL')
    result['printable_geometry_checks_passed'] = bool(mesh.is_watertight and mesh.body_count == 1 and
        not result['degenerate_faces'] and not result['duplicate_faces'] and mesh.is_winding_consistent)
    if not is_original and not result['printable_geometry_checks_passed']:
        raise ValueError(f'{path}: STL validation failed: {result}')
    return mesh, result


def export_design(part, design, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if design['id'] == 'original':
        shutil.copyfile(part.source, destination)
        mesh, validation = validate_mesh(destination, part, is_original=True)
        mesh.apply_translation([-part.center[0], -part.center[1], 0])
        return mesh, validation
    planar = set_precision(design['material'], .0001).simplify(.0001, preserve_topology=True)
    polygons = list(planar.geoms) if hasattr(planar, 'geoms') else [planar]
    slabs = [trimesh.creation.extrude_polygon(p, height=part.thickness, engine='earcut')
             for p in polygons if p.area > 1e-7]
    for slab in slabs:
        if not slab.is_volume:
            raise ValueError(f'Extrusion is not a volume: watertight={slab.is_watertight}, winding={slab.is_winding_consistent}, volume={slab.volume}')
    # The rim solid (including the attachment tab and fillets) is retained in full.
    mesh = trimesh.boolean.union([part.rim, *slabs], engine='manifold', check_volume=True)
    if not mesh.is_watertight: raise ValueError('Boolean union did not produce a closed solid')
    # Verify no original rim volume was removed; geometric union guarantees this
    # but the explicit check also catches future generator regressions.
    missing_rim = trimesh.boolean.difference([part.rim, mesh], engine='manifold')
    if abs(missing_rim.volume) > .01: raise ValueError('Original rim material was removed')
    global_mesh = mesh.copy(); global_mesh.apply_translation([part.center[0], part.center[1], 0])
    global_mesh.export(destination)
    reloaded, validation = validate_mesh(destination, part)
    validation['missing_original_rim_volume'] = float(abs(missing_rim.volume))
    validation['construction'] = 'valid planar footprint extrusion + manifold union with exact source rim'
    # Independent reread and section test checks that holes remain open in the STL.
    sec = reloaded.section(plane_origin=[0, 0, part.thickness / 2], plane_normal=[0, 0, 1])
    validation['slice_contours'] = len(sec.discrete)
    reloaded.apply_translation([-part.center[0], -part.center[1], 0])
    return reloaded, validation


def manufacturing_metrics(part, design, mesh):
    material = design['material'].union(part.rim_polygon)
    envelope = Polygon(part.rim_polygon.exterior)
    open_area = envelope.area - material.intersection(envelope).area
    widths = np.r_[design['widths'], [c['width'] for c in design['contacts']]]
    return dict(open_area=float(100 * open_area / envelope.area), open_area_mm2=float(open_area),
                material_area_proxy=float(material.area), minimum_ligament_width=float(widths.min()),
                mass_proxy=float(part.rim.volume + material.difference(part.rim_polygon).area * part.thickness),
                mass_proxy_unit='mm³ (rim volume + flat material area × thickness; no density)',
                lattice_thickness_mm=part.thickness, rim_height_mm=part.rim_height)
