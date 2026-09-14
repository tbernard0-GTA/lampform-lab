"""Relative beam-network surrogate adapted from legacy/lampform_ligament_v02.py.

All nodes lie on the measured top-surface envelope. Unknowns are XY positions.
The common rim spring parameter applies only to endpoints of explicit contact
paths. No design-specific arbitrary boundary-anchor multiplier is used.
"""
import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix

DEFAULTS = dict(boundary_anchor=2., interior_anchor=.0005, bending_weight=.01,
                max_nfev=450, tolerance=1e-7, load_steps=[.25, .5, .75, 1.])


def solve_design(part, tool, lattice, parameters=None):
    config = {**DEFAULTS, **(parameters or {})}
    nodes = lattice['nodes']; edges = lattice['edges']; n = len(nodes)
    rest = lattice['rest_length']; reference = lattice['reference_length']
    neighbors = [[] for _ in nodes]
    for e, (i, j) in enumerate(edges): neighbors[i].append((j, e)); neighbors[j].append((i, e))
    triples, pair_edges = [], []
    for i, nb in enumerate(neighbors):
        for a in range(len(nb)):
            for b in range(a + 1, len(nb)):
                triples.append((i, nb[a][0], nb[b][0])); pair_edges.append((nb[a][1], nb[b][1]))
    tri = np.array(triples); pair_edges = np.array(pair_edges)
    def cosines(xyz):
        v1 = xyz[tri[:, 1]] - xyz[tri[:, 0]]; v2 = xyz[tri[:, 2]] - xyz[tri[:, 0]]
        return np.einsum('ij,ij->i', v1, v2) / np.maximum(np.linalg.norm(v1, axis=1) * np.linalg.norm(v2, axis=1), 1e-12)
    cos0 = cosines(nodes)
    width_ratio = lattice['width'] / lattice['baseline_width']
    # Energy weights include segment length: adding sampling nodes cannot dilute
    # axial energy. Curvature proxy weights use inverse adjacent segment length.
    axial_weight = np.sqrt(width_ratio * rest / reference)
    bend_weight = np.sqrt(config['bending_weight'] *
                          np.mean(width_ratio[pair_edges] ** 3, axis=1) *
                          reference / np.mean(rest[pair_edges], axis=1))
    anchor_weights = np.full(n, config['interior_anchor'])
    anchor_weights[lattice['anchor_nodes']] = config['boundary_anchor']
    # Reference length is fixed for every design of a part, including scaled cores.
    bounds = tool['mesh'].bounds[:, :2].copy()
    bounds[0] = np.minimum(bounds[0] + .1, nodes.min(axis=0) - .1)
    bounds[1] = np.maximum(bounds[1] - .1, nodes.max(axis=0) + .1)
    pattern = lil_matrix((len(edges) + len(tri) + 2 * n, 2 * n), dtype=int)
    row = 0
    for ids in list(edges) + list(tri):
        for q in ids: pattern[row, 2*q:2*q+2] = 1
        row += 1
    for i in range(n):
        pattern[row, 2*i] = 1; pattern[row+1, 2*i+1] = 1; row += 2
    progress = 1.
    def residual(x):
        xy = x.reshape(n, 2); xyz = np.c_[xy, progress * tool['surface'](xy)]
        length = np.linalg.norm(xyz[edges[:, 1]] - xyz[edges[:, 0]], axis=1)
        axial = (length / rest - 1) * axial_weight
        bend = (cosines(xyz) - cos0) * bend_weight
        anchors = ((xy - nodes) / reference * np.sqrt(anchor_weights[:, None])).reshape(-1)
        return np.r_[axial, bend, anchors]
    initial = nodes.reshape(-1).copy(); stages = []; stage_positions = [np.c_[nodes, np.zeros(n)]]
    for progress in config['load_steps']:
        sol = least_squares(residual, initial, bounds=(np.tile(bounds[0], n), np.tile(bounds[1], n)),
                            jac_sparsity=pattern.tocsr(), tr_solver='lsmr', max_nfev=config['max_nfev'],
                            xtol=config['tolerance'], ftol=config['tolerance'], gtol=config['tolerance'])
        initial = sol.x
        stage_xy = sol.x.reshape(n, 2)
        stage_positions.append(np.c_[stage_xy, progress * tool['surface'](stage_xy)])
        stages.append(dict(progress=progress, success=bool(sol.success), nfev=sol.nfev,
                           cost=float(sol.cost), optimality=float(sol.optimality)))
    xy = sol.x.reshape(n, 2); xyz = np.c_[xy, tool['surface'](xy)]
    strain = 100 * (np.linalg.norm(xyz[edges[:, 1]] - xyz[edges[:, 0]], axis=1) / rest - 1)
    if not np.isfinite(strain).all(): raise ValueError('Non-finite solver result')
    # Equal weight for each physical parent ligament, using its most-demanded
    # segment, so a finely sampled compliant path cannot dilute percentiles.
    parent_demand = np.array([max(0., strain[lattice['parent'] == p].max()) for p in range(len(lattice['parent_paths']))])
    shifts = np.linalg.norm(xy - nodes, axis=1)
    metrics = {f'p{q}': float(np.percentile(parent_demand, q)) for q in [50, 90, 95, 99]}
    metrics.update(mean=float(parent_demand.mean()), maximum=float(parent_demand.max()), std=float(parent_demand.std()),
                   mean_xy_feed=float(shifts[:lattice['core_node_count']].mean()),
                   max_xy_feed=float(shifts[:lattice['core_node_count']].max()),
                   critical_edges=int(np.sum(parent_demand > 20)), edge_count=len(parent_demand))
    for threshold in [5, 10, 20, 30]: metrics[f'above_{threshold}_pct'] = float(100 * np.mean(parent_demand > threshold))
    return dict(nodes=nodes, edges=edges, formed_nodes=xyz, stage_positions=stage_positions, edge_strain=strain, displacement=xyz - np.c_[nodes, np.zeros(n)],
                parent_demand=parent_demand, metrics=metrics,
                solver=dict(success=bool(sol.success), message=sol.message, nfev=sum(s['nfev'] for s in stages), cost=float(sol.cost),
                            optimality=float(sol.optimality), parameters=config, stages=stages))
