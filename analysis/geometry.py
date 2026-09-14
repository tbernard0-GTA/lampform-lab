from dataclasses import dataclass
from pathlib import Path
import hashlib
import numpy as np
import trimesh
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union, nearest_points
from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / 'legacy/lampform_lab_v01'
PAIRS = [('hab2', 'HAB-2', 'obj_1_HAB-2.stl', 'obj_2_Mold.stl'),
         ('submerged', 'Sub-Merged', 'obj_3_Sub-merged body.stl', 'obj_4_Push.stl')]


def footprint(mesh):
    polygons = [Polygon(t[:, :2]) for t in mesh.triangles]
    return unary_union([p for p in polygons if p.area > 1e-9]).buffer(0)


@dataclass
class Part:
    id: str
    name: str
    source: Path
    mesh: object
    rim: object
    rim_polygon: object
    lattice_polygon: object
    cells: list
    centers: np.ndarray
    center: np.ndarray
    thickness: float
    rim_height: float


def load_part(spec):
    part_id, name, filename, _ = spec
    source = LEGACY / filename
    mesh = trimesh.load_mesh(source, process=True)
    center = mesh.bounds.mean(axis=0)
    mesh.apply_translation([-center[0], -center[1], 0])
    # Face connectivity isolates the intact, watertight rim; defective lattice
    # sheets remain untouched in the archive and are reconstructed only for candidates.
    labels = trimesh.graph.connected_component_labels(mesh.face_adjacency, node_count=len(mesh.faces))
    top_face = int(np.argmax(mesh.triangles[:, :, 2].max(axis=1)))
    rim_mask = labels == labels[top_face]
    rim = mesh.submesh([rim_mask], append=True, repair=False)
    if not rim.is_watertight:
        raise ValueError('Could not isolate the original closed rim')
    lattice_mesh = mesh.submesh([~rim_mask], append=True, repair=False)
    thickness = float(lattice_mesh.bounds[1, 2] - lattice_mesh.bounds[0, 2])
    section = mesh.section(plane_normal=[0, 0, 1], plane_origin=[0, 0, thickness / 2])
    cells = [Polygon(c[:, :2]).simplify(.05, preserve_topology=True) for c in section.discrete
             if Polygon(c[:, :2]).is_valid and 35 < Polygon(c[:, :2]).area < 50]
    cells.sort(key=lambda p: (p.centroid.y, p.centroid.x))
    if len(cells) != 65:
        raise ValueError(f'Expected the supplied 65-cell geometry, found {len(cells)}')
    return Part(part_id, name, source, mesh, rim, footprint(rim), footprint(lattice_mesh), cells,
                np.array([[p.centroid.x, p.centroid.y] for p in cells]), center, thickness,
                float(mesh.extents[2]))


def load_tool(spec):
    mesh = trimesh.load_mesh(LEGACY / spec[3], process=True)
    center = mesh.bounds.mean(axis=0)
    mesh.apply_translation([-center[0], -center[1], 0])
    envelope = {}
    for xy, z in zip(np.round(mesh.vertices[:, :2], 5), mesh.vertices[:, 2]):
        key = tuple(xy)
        envelope[key] = max(envelope.get(key, -np.inf), float(z))
    points = np.array(list(envelope)); values = np.array(list(envelope.values()))
    linear = LinearNDInterpolator(points, values, fill_value=np.nan)
    nearest = NearestNDInterpolator(points, values)
    def surface(q):
        q = np.atleast_2d(q)
        z = np.asarray(linear(q)).reshape(-1)
        outside = ~np.isfinite(z)
        z[outside] = nearest(q[outside])
        return z
    return dict(mesh=mesh, surface=surface, source=LEGACY / spec[3])


def cross_width(material, a, b, maximum=8.):
    direction = b - a
    normal = np.array([-direction[1], direction[0]]) / np.linalg.norm(direction)
    widths = []
    for t in [.3, .5, .7]:
        p = a + t * direction
        line = LineString([p - maximum * normal / 2, p + maximum * normal / 2])
        intersection = line.intersection(material)
        lines = list(intersection.geoms) if hasattr(intersection, 'geoms') else [intersection]
        selected = [l.length for l in lines if l.distance(Point(p)) < 1e-5]
        widths.append(max(selected, default=0.))
    return min(widths)


def rim_contacts(part, nodes, boundary):
    material = part.lattice_polygon.union(part.rim_polygon)
    contacts = []
    for i in np.where(boundary)[0]:
        p = nodes[i]
        q = np.array(nearest_points(Point(p), part.rim_polygon)[1].coords[0])
        delta = q - p; length = np.linalg.norm(delta)
        if length < .15:
            continue
        q = q + delta / length * .2  # finite overlap with the retained original rim
        if material.buffer(.025).covers(LineString([p, q])):
            width = cross_width(material.buffer(.0001), p, q)
            if width >= .8:
                contacts.append(dict(node=int(i), end=q, width=width))
    if len(contacts) < 6:
        raise ValueError('Too few material-supported contacts to represent the rim')
    return contacts


def mesh_json(mesh):
    return dict(positions=np.round(mesh.vertices, 5).reshape(-1).tolist(), indices=mesh.faces.reshape(-1).tolist(),
                dimensions=np.round(mesh.extents, 5).tolist())


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
