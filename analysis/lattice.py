import numpy as np
from shapely.geometry import LineString, Point
from .geometry import cross_width


def base_network(centers):
    # Same centerline construction as legacy v0.2, with detected pitch.
    distances = np.linalg.norm(centers[:, None] - centers[None, :], axis=2)
    distances[distances < 1e-4] = np.inf
    pitch = round(float(np.median(distances.min(axis=1))), 2)
    side = pitch / np.sqrt(3)
    angles = np.deg2rad([90, 30, -30, -90, -150, 150])
    offsets = np.c_[side * np.cos(angles), side * np.sin(angles)]
    lookup, nodes, counts = {}, [], {}
    cell_edges = []
    for c in centers:
        ids = []
        for point in c + offsets:
            # STL triangulation perturbs nominally coincident corners. Merge
            # within 0.03 mm, rather than the legacy decimal-key discontinuity.
            match = next((i for i, p in enumerate(nodes) if np.linalg.norm(p - point) < .03), None)
            if match is None:
                match = len(nodes); nodes.append(point)
            ids.append(match)
        es = [tuple(sorted((ids[i], ids[(i + 1) % 6]))) for i in range(6)]
        for edge in es: counts[edge] = counts.get(edge, 0) + 1
        cell_edges.append(es)
    edges = sorted(counts); index = {e: i for i, e in enumerate(edges)}
    boundary = np.zeros(len(nodes), dtype=bool)
    for edge, count in counts.items():
        if count == 1: boundary[list(edge)] = True
    return dict(nodes=np.array(nodes), edges=np.array(edges), boundary=boundary, pitch=pitch,
                cell_edges=np.array([[index[e] for e in es] for es in cell_edges]))


def wave_path(a, b, amplitude, segments=8):
    delta = b - a; length = np.linalg.norm(delta)
    normal = np.array([-delta[1], delta[0]]) / length
    t = np.linspace(0, 1, segments + 1)
    # Single smooth S; zero offset and zero tangent offset at both endpoints.
    offset = amplitude * np.sin(2 * np.pi * t) * np.sin(np.pi * t)
    return a + t[:, None] * delta + offset[:, None] * normal


def assemble_network(base, paths, widths, contacts, thickness, baseline_width):
    nodes = base['nodes'].tolist()
    edges, edge_width, parent, path_ratio, kinds = [], [], [], [], []
    anchor_nodes = []
    parent_paths = []
    def append_path(a_index, b_index, path, width, parent_id, kind):
        ids = [a_index]
        for p in path[1:-1]: ids.append(len(nodes)); nodes.append(p.tolist())
        ids.append(b_index)
        length = np.linalg.norm(np.diff(path, axis=0), axis=1).sum()
        ratio = length / np.linalg.norm(path[-1] - path[0])
        for a, b in zip(ids[:-1], ids[1:]):
            edges.append([a, b]); edge_width.append(width); parent.append(parent_id)
            path_ratio.append(ratio); kinds.append(kind)
        parent_paths.append(path.tolist())
    for i, ((a, b), path, width) in enumerate(zip(base['edges'], paths, widths)):
        append_path(int(a), int(b), path, width, i, 'lattice')
    for i, contact in enumerate(contacts):
        end = len(nodes); nodes.append(contact['path'][-1].tolist()); anchor_nodes.append(end)
        append_path(contact['node'], end, contact['path'], contact['width'], len(paths) + i, 'transition')
    nodes = np.array(nodes); edges = np.array(edges); edge_width = np.array(edge_width)
    lengths = np.linalg.norm(nodes[edges[:, 0]] - nodes[edges[:, 1]], axis=1)
    reference = base['pitch'] / np.sqrt(3)
    ratio = edge_width / baseline_width
    return dict(nodes=nodes, edges=edges, width=edge_width, thickness=np.full(len(edges), thickness),
                rest_length=lengths, axial_stiffness_proxy=ratio * reference / lengths,
                bending_stiffness_proxy=ratio ** 3 * (reference / lengths) ** 3,
                compliance_factor=np.array(path_ratio), boundary_factor=np.ones(len(edges)),
                anchor_nodes=np.array(anchor_nodes), parent=np.array(parent), kinds=kinds,
                reference_length=reference, baseline_width=baseline_width, parent_paths=parent_paths,
                core_node_count=len(base['nodes']))
