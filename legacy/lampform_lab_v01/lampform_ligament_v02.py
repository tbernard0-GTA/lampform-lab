from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import trimesh
from shapely.geometry import Polygon
from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix
import matplotlib.pyplot as plt
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results_v02"
OUT.mkdir(exist_ok=True)

PAIRS = [
    ("hab2_mold", "HAB-2 → Mold", ROOT / "obj_1_HAB-2.stl", ROOT / "obj_2_Mold.stl"),
    ("submerged_push", "Sub-merged body → Push", ROOT / "obj_3_Sub-merged body.stl", ROOT / "obj_4_Push.stl"),
]

PITCH = 8.0
HEX_SIDE = 4.0
CURRENT_GAP = PITCH - np.sqrt(3.0) * HEX_SIDE
BEND_WEIGHT = 0.01
BASELINE_BOUNDARY_ANCHOR = 2.0
INTERIOR_ANCHOR = 0.0005
BOUNDARY_SWEEP = [5.0, 2.0, 1.0, 0.5, 0.2, 0.05]


def centers_from_lamp(path: Path):
    mesh = trimesh.load_mesh(path, process=True)
    center = mesh.bounds.mean(axis=0)
    section = mesh.section(plane_origin=[0, 0, 0.5], plane_normal=[0, 0, 1])
    cells = []
    for arr in section.discrete:
        poly = Polygon(arr[:, :2] - center[:2])
        if poly.is_valid and 35 < poly.area < 50:
            cells.append(poly.simplify(0.05, preserve_topology=True))
    cells = sorted(cells, key=lambda p: (p.centroid.y, p.centroid.x))
    centers = np.array([[p.centroid.x, p.centroid.y] for p in cells])
    return centers


def top_surface(path: Path):
    mesh = trimesh.load_mesh(path, process=True)
    center = mesh.bounds.mean(axis=0)
    xy = mesh.vertices[:, :2] - center[:2]
    envelope = {}
    for q, z in zip(np.round(xy, 5), mesh.vertices[:, 2]):
        key = tuple(q)
        envelope[key] = max(envelope.get(key, -np.inf), float(z))
    pts = np.array(list(envelope.keys()), float)
    vals = np.array(list(envelope.values()), float)
    linear = LinearNDInterpolator(pts, vals, fill_value=np.nan)
    nearest = NearestNDInterpolator(pts, vals)

    def zfun(q):
        q = np.atleast_2d(np.asarray(q, float))
        z = np.asarray(linear(q), float).reshape(-1)
        missing = np.isnan(z)
        if np.any(missing):
            z[missing] = np.asarray(nearest(q[missing]), float).reshape(-1)
        return z

    return mesh, center, zfun


def ligament_network(cell_centers):
    # Voronoi centerline of an ideal triangular packing, reconstructed analytically.
    mid_hex_side = PITCH / np.sqrt(3.0)
    angles = np.deg2rad([90, 30, -30, -90, -150, 150])
    offsets = np.column_stack([mid_hex_side * np.cos(angles), mid_hex_side * np.sin(angles)])

    node_lookup = {}
    nodes = []
    edges = set()
    edge_use = {}

    def node_id(point):
        key = tuple(np.round(point, 4))
        if key not in node_lookup:
            node_lookup[key] = len(nodes)
            nodes.append(point.copy())
        return node_lookup[key]

    for center in cell_centers:
        ids = [node_id(center + off) for off in offsets]
        for i in range(6):
            edge = tuple(sorted((ids[i], ids[(i + 1) % 6])))
            edges.add(edge)
            edge_use[edge] = edge_use.get(edge, 0) + 1

    nodes = np.asarray(nodes, float)
    edges = np.asarray(sorted(edges), int)
    boundary = np.zeros(len(nodes), dtype=bool)
    for edge, count in edge_use.items():
        if count == 1:
            boundary[list(edge)] = True
    return nodes, edges, boundary


def angle_triplets(nodes, edges):
    neighbors = [[] for _ in range(len(nodes))]
    for i, j in edges:
        neighbors[i].append(j)
        neighbors[j].append(i)
    triplets = []
    for i, nb in enumerate(neighbors):
        for a in range(len(nb)):
            for b in range(a + 1, len(nb)):
                j, k = nb[a], nb[b]
                v1 = nodes[j] - nodes[i]
                v2 = nodes[k] - nodes[i]
                cos0 = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                triplets.append((i, j, k, cos0))
    return triplets


def solve_network(nodes, edges, boundary, zfun, tool, tool_center, boundary_anchor):
    n = len(nodes)
    rest = np.linalg.norm(nodes[edges[:, 0]] - nodes[edges[:, 1]], axis=1)
    triplets = angle_triplets(nodes, edges)
    tri = np.array([[t[0], t[1], t[2]] for t in triplets], int)
    cos0 = np.array([t[3] for t in triplets])

    local_bounds = np.column_stack([
        tool.bounds[:, 0] - tool_center[0],
        tool.bounds[:, 1] - tool_center[1],
    ])
    xmin, ymin = local_bounds[0]
    xmax, ymax = local_bounds[1]
    lower = np.tile([xmin + 0.1, ymin + 0.1], n)
    upper = np.tile([xmax - 0.1, ymax - 0.1], n)

    weights = np.where(boundary, boundary_anchor, INTERIOR_ANCHOR)
    scale = PITCH / np.sqrt(3.0)

    # Sparse finite-difference pattern: each residual sees only local graph nodes.
    rows = len(edges) + len(triplets) + 2 * n
    pattern = lil_matrix((rows, 2 * n), dtype=int)
    r = 0
    for i, j in edges:
        pattern[r, 2*i:2*i+2] = 1
        pattern[r, 2*j:2*j+2] = 1
        r += 1
    for i, j, k, _ in triplets:
        for q in (i, j, k):
            pattern[r, 2*q:2*q+2] = 1
        r += 1
    for i in range(n):
        pattern[r, 2*i] = 1
        r += 1
        pattern[r, 2*i+1] = 1
        r += 1

    def residual(flat):
        xy = flat.reshape(n, 2)
        xyz = np.column_stack([xy, zfun(xy)])
        lengths = np.linalg.norm(xyz[edges[:, 0]] - xyz[edges[:, 1]], axis=1)
        axial = (lengths - rest) / rest

        v1 = xyz[tri[:, 1]] - xyz[tri[:, 0]]
        v2 = xyz[tri[:, 2]] - xyz[tri[:, 0]]
        cos = np.einsum("ij,ij->i", v1, v2) / (
            np.linalg.norm(v1, axis=1) * np.linalg.norm(v2, axis=1) + 1e-12
        )
        bending = np.sqrt(BEND_WEIGHT) * (cos - cos0)
        anchors = ((xy - nodes) / scale * np.sqrt(weights[:, None])).reshape(-1)
        return np.concatenate([axial, bending, anchors])

    solution = least_squares(
        residual,
        nodes.reshape(-1),
        bounds=(lower, upper),
        jac_sparsity=pattern.tocsr(),
        tr_solver="lsmr",
        max_nfev=100,
        xtol=1e-7,
        ftol=1e-7,
        gtol=1e-7,
    )

    xy = solution.x.reshape(n, 2)
    xyz = np.column_stack([xy, zfun(xy)])
    lengths = np.linalg.norm(xyz[edges[:, 0]] - xyz[edges[:, 1]], axis=1)
    stretch = lengths / rest
    return solution, xy, xyz, rest, stretch


def direct_state(nodes, edges, zfun):
    xyz = np.column_stack([nodes, zfun(nodes)])
    rest = np.linalg.norm(nodes[edges[:, 0]] - nodes[edges[:, 1]], axis=1)
    lengths = np.linalg.norm(xyz[edges[:, 0]] - xyz[edges[:, 1]], axis=1)
    return xyz, lengths / rest


def edge_table(nodes, edges, boundary, rest, direct_stretch, xy, xyz, relaxed_stretch):
    boundary_edge = boundary[edges[:, 0]] | boundary[edges[:, 1]]
    return pd.DataFrame({
        "edge": np.arange(len(edges)),
        "node_i": edges[:, 0],
        "node_j": edges[:, 1],
        "x_i_flat_mm": nodes[edges[:, 0], 0],
        "y_i_flat_mm": nodes[edges[:, 0], 1],
        "x_j_flat_mm": nodes[edges[:, 1], 0],
        "y_j_flat_mm": nodes[edges[:, 1], 1],
        "rest_length_mm": rest,
        "direct_stretch": direct_stretch,
        "relaxed_stretch": relaxed_stretch,
        "relaxed_strain_pct": 100.0 * (relaxed_stretch - 1.0),
        "boundary_edge": boundary_edge,
        "x_i_relaxed_mm": xy[edges[:, 0], 0],
        "y_i_relaxed_mm": xy[edges[:, 0], 1],
        "z_i_relaxed_mm": xyz[edges[:, 0], 2],
        "x_j_relaxed_mm": xy[edges[:, 1], 0],
        "y_j_relaxed_mm": xy[edges[:, 1], 1],
        "z_j_relaxed_mm": xyz[edges[:, 1], 2],
    })


def binned_line_trace(xyz, edges, stretch, lo, hi, name, visible):
    x, y, z = [], [], []
    strain = 100.0 * (stretch - 1.0)
    mask = (strain >= lo) & (strain < hi)
    for i, j in edges[mask]:
        x += [xyz[i, 0], xyz[j, 0], None]
        y += [xyz[i, 1], xyz[j, 1], None]
        z += [xyz[i, 2], xyz[j, 2], None]
    return go.Scatter3d(x=x, y=y, z=z, mode="lines", name=name, visible=visible)


def viewer(label, tool, tool_center, nodes, edges, direct_xyz, direct_stretch, relaxed_xyz, relaxed_stretch, output):
    v = tool.vertices.copy()
    v[:, :2] -= tool_center[:2]
    f = tool.faces
    traces = [go.Mesh3d(x=v[:,0], y=v[:,1], z=v[:,2], i=f[:,0], j=f[:,1], k=f[:,2], opacity=0.28, name="tool", hoverinfo="skip")]
    bins = [(-1e9, 10, "≤10%"), (10, 20, "10–20%"), (20, 35, "20–35%"), (35, 1e9, ">35%")]
    for lo, hi, txt in bins:
        traces.append(binned_line_trace(direct_xyz, edges, direct_stretch, lo, hi, "direct " + txt, True))
    for lo, hi, txt in bins:
        traces.append(binned_line_trace(relaxed_xyz, edges, relaxed_stretch, lo, hi, "relaxed " + txt, False))
    fig = go.Figure(traces)
    fig.update_layout(
        title=label + " — ligament network v0.2",
        scene=dict(xaxis_title="X [mm]", yaxis_title="Y [mm]", zaxis_title="Z [mm]", aspectmode="data"),
        updatemenus=[dict(buttons=[
            dict(label="Direct projection", method="update", args=[{"visible": [True, True, True, True, True, False, False, False, False]}]),
            dict(label="Relaxed ligament network", method="update", args=[{"visible": [True, False, False, False, False, True, True, True, True]}]),
        ], x=0.01, y=1.08)],
        margin=dict(l=0, r=0, t=70, b=0),
    )
    fig.write_html(output, include_plotlyjs=True)


def sensitivity_plot(df, output, title):
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    ax.plot(df["boundary_anchor"], df["mean_strain_pct"], marker="o", label="mean")
    ax.plot(df["boundary_anchor"], df["p95_strain_pct"], marker="o", label="P95")
    ax.plot(df["boundary_anchor"], df["max_strain_pct"], marker="o", label="max")
    ax.set_xscale("log")
    ax.invert_xaxis()
    ax.set_xlabel("boundary anchoring parameter (stiffer → left)")
    ax.set_ylabel("effective ligament axial strain [%]")
    ax.set_title(title)
    ax.legend()
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def metrics(stretch):
    return {
        "mean_strain_pct": float(100.0 * (np.mean(stretch) - 1.0)),
        "p95_strain_pct": float(100.0 * (np.percentile(stretch, 95) - 1.0)),
        "max_strain_pct": float(100.0 * (np.max(stretch) - 1.0)),
    }


def main():
    summary = []
    for slug, label, lamp_path, tool_path in PAIRS:
        centers = centers_from_lamp(lamp_path)
        tool, tool_center, zfun = top_surface(tool_path)
        nodes, edges, boundary = ligament_network(centers)
        direct_xyz, direct_stretch = direct_state(nodes, edges, zfun)

        sol, xy, xyz, rest, relaxed_stretch = solve_network(
            nodes, edges, boundary, zfun, tool, tool_center, BASELINE_BOUNDARY_ANCHOR
        )
        edge_table(nodes, edges, boundary, rest, direct_stretch, xy, xyz, relaxed_stretch).to_csv(
            OUT / f"{slug}_ligaments.csv", index=False
        )
        viewer(label, tool, tool_center, nodes, edges, direct_xyz, direct_stretch, xyz, relaxed_stretch, OUT / f"{slug}_ligament_3d.html")

        sweep_rows = []
        for anchor in BOUNDARY_SWEEP:
            _, xy_s, _, _, stretch_s = solve_network(nodes, edges, boundary, zfun, tool, tool_center, anchor)
            row = {"boundary_anchor": anchor, **metrics(stretch_s)}
            shifts = np.linalg.norm(xy_s - nodes, axis=1)
            row["mean_xy_feed_mm"] = float(shifts.mean())
            row["max_xy_feed_mm"] = float(shifts.max())
            sweep_rows.append(row)
        sweep = pd.DataFrame(sweep_rows)
        sweep.to_csv(OUT / f"{slug}_boundary_sensitivity.csv", index=False)
        sensitivity_plot(sweep, OUT / f"{slug}_boundary_sensitivity.png", label + " — sensitivity to rim anchoring")

        shifts = np.linalg.norm(xy - nodes, axis=1)
        summary.append({
            "pair": label,
            "cells": int(len(centers)),
            "ligament_nodes": int(len(nodes)),
            "ligaments": int(len(edges)),
            "current_nominal_gap_mm": float(CURRENT_GAP),
            "baseline_boundary_anchor": BASELINE_BOUNDARY_ANCHOR,
            "solver_success": bool(sol.success),
            "direct": metrics(direct_stretch),
            "relaxed": metrics(relaxed_stretch),
            "mean_xy_feed_mm": float(shifts.mean()),
            "max_xy_feed_mm": float(shifts.max()),
        })

    (OUT / "summary_v02.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
