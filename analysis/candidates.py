from copy import deepcopy
import numpy as np
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from shapely.affinity import scale as scale_polygon
from .geometry import cross_width
from .lattice import wave_path, assemble_network

DESIGNS = [('original', 'Original'), ('gradient', 'Gradient'),
           ('gradient_boundary', 'Gradient + Compliant Boundary'), ('compliant', 'Compliant')]
PARAMETERS = dict(gradient_strength=.10, smoothing_mm=12., critical_percentile=75.,
                  compliant_width_mm=.95, wave_amplitude_mm=.65, boundary_core_scale=.90,
                  boundary_wave_amplitude_mm=1.2, minimum_ligament_mm=.8, minimum_gap_mm=.4,
                  minimum_hole_scale=.75)


def make_design(part, base, source_contacts, design_id, baseline=None, parameters=None):
    config = {**PARAMETERS, **(parameters or {})}
    graph = deepcopy(base)
    material = part.lattice_polygon
    holes = list(part.cells)
    scales = np.ones(len(holes)); severity = np.zeros(len(holes))
    parent_baseline = baseline['parent_demand'][:len(base['edges'])] if baseline is not None else np.zeros(len(base['edges']))
    if design_id in ('gradient', 'gradient_boundary'):
        cell_demand = parent_baseline[base['cell_edges']].max(axis=1)
        distances = np.linalg.norm(part.centers[:, None] - part.centers[None, :], axis=2)
        kernel = np.exp(-.5 * (distances / config['smoothing_mm']) ** 2)
        smoothed = kernel @ cell_demand / kernel.sum(axis=1)
        severity = np.clip((smoothed - np.percentile(smoothed, 10)) /
                           max(np.percentile(smoothed, 95) - np.percentile(smoothed, 10), 1e-6), 0, 1)
        scales = np.maximum(config['minimum_hole_scale'], 1 - config['gradient_strength'] * severity)
        holes = [scale_polygon(p, xfact=s, yfact=s, origin='centroid') for p, s in zip(part.cells, scales)]
        additions = unary_union([a.difference(b) for a, b in zip(part.cells, holes)])
        material = material.union(additions).buffer(0)
    contacts = []
    if design_id == 'gradient_boundary':
        factor = config['boundary_core_scale']
        support = material.union(part.rim_polygon).buffer(.0001)
        core_widths = [cross_width(support, *base['nodes'][edge]) * factor for edge in base['edges']]
        graph['nodes'] *= factor
        material = scale_polygon(material, xfact=factor, yfact=factor, origin=(0, 0))
        # Peripheral centerlines formerly supported by the rim must be solid
        # in the detached core, not floating proxy lines outside its footprint.
        core_supports = [LineString(graph['nodes'][edge]).buffer(width / 2, quad_segs=8)
                         for edge, width in zip(graph['edges'], core_widths)]
        material = material.union(unary_union(core_supports)).buffer(0)
        holes = [scale_polygon(p, xfact=factor, yfact=factor, origin=(0, 0)) for p in holes]
        for c in source_contacts:
            a = graph['nodes'][c['node']]; b = c['end']
            amplitude = min(config['boundary_wave_amplitude_mm'], np.linalg.norm(b - a) * .25)
            path = wave_path(a, b, amplitude)
            contacts.append(dict(node=c['node'], path=path, width=config['compliant_width_mm']))
        material = material.union(unary_union([LineString(c['path']).buffer(c['width'] / 2, quad_segs=8) for c in contacts])).buffer(0)
    else:
        for c in source_contacts:
            a = graph['nodes'][c['node']]; b = c['end']
            width = cross_width(material.union(part.rim_polygon).buffer(.0001), a, b)
            contacts.append(dict(node=c['node'], path=np.array([a, b]), width=width))
    paths = [graph['nodes'][edge].copy() for edge in graph['edges']]
    combined = material.union(part.rim_polygon).buffer(.0001)
    widths = np.array([cross_width(combined, *p) for p in paths])
    changed = []
    if design_id == 'compliant':
        threshold = np.percentile(parent_baseline, config['critical_percentile'])
        cuts, additions = [], []
        # The same threshold is applied to both parts. Perimeter edges stay
        # straight: this design isolates interior ligament compliance.
        for i, (edge, path) in enumerate(zip(graph['edges'], paths)):
            if parent_baseline[i] < threshold or graph['boundary'][edge].any(): continue
            a, b = path; direction = (b - a) / np.linalg.norm(b - a)
            new_path = wave_path(a, b, config['wave_amplitude_mm'])
            corridor = LineString([a + .72 * direction, b - .72 * direction]).buffer(widths[i] / 2 + .18, cap_style=2)
            wave = LineString(new_path).buffer(config['compliant_width_mm'] / 2, quad_segs=8)
            cuts.append(corridor); additions.append(wave)
            paths[i] = new_path; widths[i] = config['compliant_width_mm']; changed.append(i)
        material = material.difference(unary_union(cuts)).union(unary_union(additions)).buffer(0)
    if design_id != 'original':
        # Close tiny source junction notches along modeled paths, guaranteeing
        # an explicit 0.8 mm minimum swept load path without changing the rim.
        supports = [LineString(path).buffer(config['minimum_ligament_mm'] / 2, quad_segs=8) for path in paths]
        supports += [LineString(c['path']).buffer(config['minimum_ligament_mm'] / 2, quad_segs=8) for c in contacts]
        material = material.union(unary_union(supports)).buffer(0)
    source_widths = np.array([cross_width(part.lattice_polygon.union(part.rim_polygon).buffer(.0001), *base['nodes'][edge]) for edge in base['edges']])
    baseline_width = float(np.median(source_widths[~base['boundary'][base['edges']].any(axis=1)]))
    if np.min(widths) < config['minimum_ligament_mm']:
        raise ValueError(f'{part.id}/{design_id}: narrow ligament {np.min(widths):.4f} mm')
    # All modeled paths must lie in the actual exported footprint; their swept
    # widths are tested separately, including every compliant segment.
    for edge_index, path in enumerate(paths):
        if not material.union(part.rim_polygon).buffer(.025).covers(LineString(path)):
            raise ValueError(f'{part.id}/{design_id}: ligament {edge_index} is outside the solid: {LineString(path).difference(material.union(part.rim_polygon).buffer(.025)).length:.5f} mm')
    lattice = assemble_network(graph, paths, widths, contacts, part.thickness, baseline_width)
    # Read the actual void containing each cell center after every cut/union.
    # Compliant paths change neighboring openings too; do not publish the old hexagons.
    if design_id != 'original':
        solid = material.union(part.rim_polygon)
        voids = [Polygon(ring) for poly in (solid.geoms if hasattr(solid, 'geoms') else [solid])
                 for ring in poly.interiors]
        actual = []
        for hole in holes:
            matches = [p for p in voids if p.covers(hole.centroid)]
            if len(matches) != 1: raise ValueError('Cell opening lost or ambiguous')
            opening = matches[0]
            # A 0.4 mm probe must fit the main opening. This is not a global
            # minimum-clearance claim for tapered corners or small peripheral slots.
            if opening.buffer(-config['minimum_gap_mm'] / 2).is_empty:
                raise ValueError('Cell aperture below minimum gap probe')
            actual.append(opening)
        holes = actual
    return dict(id=design_id, material=material, holes=holes, hole_scales=scales,
                severity=severity, lattice=lattice, paths=paths, widths=widths,
                contacts=contacts, changed_edges=changed, parameters=config,
                cell_centers=np.array([[p.centroid.x, p.centroid.y] for p in holes]),
                baseline_cell_demand=parent_baseline[base['cell_edges']].max(axis=1),
                original_cell_width=source_widths[base['cell_edges']].mean(axis=1),
                candidate_cell_width=widths[base['cell_edges']].mean(axis=1), cell_parent_indices=base['cell_edges'],
                original_hole_size=np.array([np.sqrt(p.area * 2 / np.sqrt(3)) for p in part.cells]),
                hole_size=np.array([np.sqrt(p.area * 2 / np.sqrt(3)) for p in holes]))
