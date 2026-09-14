from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import trimesh
from shapely.geometry import Polygon
from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull, Delaunay
import matplotlib.pyplot as plt
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)

CONFIG = {
    "section_z_mm": 0.5,
    "cell_area_range_mm2": [35.0, 50.0],
    "neighbor_max_distance_mm": 8.5,
    "boundary_anchor_weight": 2.5,
    "interior_anchor_weight": 0.01,
    "current_hex_side_mm": 4.0,
    "current_pitch_mm": 8.0,
    "compensation_fraction": 0.65,
    "design_lambda_cap": 1.22,
    "min_hex_side_mm": 2.8,
}

PAIRS = [
    {
        "slug": "hab2_mold",
        "label": "HAB-2 → Mold",
        "lamp": ROOT / "obj_1_HAB-2.stl",
        "tool": ROOT / "obj_2_Mold.stl",
    },
    {
        "slug": "submerged_push",
        "label": "Sub-merged body → Push",
        "lamp": ROOT / "obj_3_Sub-merged body.stl",
        "tool": ROOT / "obj_4_Push.stl",
    },
]


def extract_cells(mesh_path: Path, z: float):
    mesh = trimesh.load_mesh(mesh_path, process=True)
    center = mesh.bounds.mean(axis=0)
    sec = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if sec is None:
        raise RuntimeError(f"No section found in {mesh_path.name} at z={z}")

    cells, other = [], []
    amin, amax = CONFIG["cell_area_range_mm2"]
    for arr in sec.discrete:
        xy = arr[:, :2] - center[:2]
        poly = Polygon(xy)
        if not poly.is_valid or poly.area <= 1e-3:
            continue
        if amin < poly.area < amax:
            cells.append(poly.simplify(0.05, preserve_topology=True))
        else:
            other.append(poly)

    cells = sorted(cells, key=lambda p: (p.centroid.y, p.centroid.x))
    outer = max(other, key=lambda p: p.area)
    return mesh, center, cells, outer


def surface_interpolator(mesh_path: Path, rounding: int = 5):
    mesh = trimesh.load_mesh(mesh_path, process=True)
    center = mesh.bounds.mean(axis=0)
    xy = mesh.vertices[:, :2] - center[:2]
    z = mesh.vertices[:, 2]

    envelope = {}
    for key, value in zip(map(tuple, np.round(xy, rounding)), z):
        envelope[key] = max(envelope.get(key, -np.inf), float(value))
    points = np.asarray(list(envelope.keys()), dtype=float)
    values = np.asarray(list(envelope.values()), dtype=float)

    linear = LinearNDInterpolator(points, values, fill_value=np.nan)
    nearest = NearestNDInterpolator(points, values)

    def zfun(q):
        q = np.atleast_2d(np.asarray(q, dtype=float))
        out = np.asarray(linear(q), dtype=float).reshape(-1)
        missing = np.isnan(out)
        if np.any(missing):
            out[missing] = np.asarray(nearest(q[missing]), dtype=float).reshape(-1)
        return out

    return mesh, center, zfun


def build_neighbor_graph(points: np.ndarray):
    tri = Delaunay(points, qhull_options="QJ")
    edges = set()
    cutoff = CONFIG["neighbor_max_distance_mm"]
    for simplex in tri.simplices:
        for a, b in [(0, 1), (1, 2), (2, 0)]:
            i, j = sorted((int(simplex[a]), int(simplex[b])))
            if np.linalg.norm(points[i] - points[j]) <= cutoff:
                edges.add((i, j))
    return np.asarray(sorted(edges), dtype=int)


def evaluate_edges(xy: np.ndarray, edges: np.ndarray, zfun, rest_lengths=None):
    z = zfun(xy)
    xyz = np.column_stack([xy, z])
    if rest_lengths is None:
        rest_lengths = np.linalg.norm(xy[edges[:, 0]] - xy[edges[:, 1]], axis=1)
    lengths = np.linalg.norm(xyz[edges[:, 0]] - xyz[edges[:, 1]], axis=1)
    return xyz, rest_lengths, lengths / rest_lengths


def relax_drape(points: np.ndarray, edges: np.ndarray, zfun, tool_mesh, tool_center):
    n = len(points)
    hull = ConvexHull(points)
    boundary = np.zeros(n, dtype=bool)
    boundary[hull.vertices] = True
    rest = np.linalg.norm(points[edges[:, 0]] - points[edges[:, 1]], axis=1)

    tool_local_bounds = np.column_stack([
        tool_mesh.bounds[:, 0] - tool_center[0],
        tool_mesh.bounds[:, 1] - tool_center[1],
    ])
    xmin, ymin = tool_local_bounds[0]
    xmax, ymax = tool_local_bounds[1]
    lb = np.tile([xmin + 0.25, ymin + 0.25], n)
    ub = np.tile([xmax - 0.25, ymax - 0.25], n)

    bweight = CONFIG["boundary_anchor_weight"]
    iweight = CONFIG["interior_anchor_weight"]
    scale = CONFIG["current_pitch_mm"]

    def residual(flat):
        xy = flat.reshape(n, 2)
        xyz, _, stretch = evaluate_edges(xy, edges, zfun, rest)
        edge_res = stretch - 1.0
        weights = np.where(boundary, bweight, iweight)
        anchor = ((xy - points) / scale * np.sqrt(weights[:, None])).reshape(-1)
        centroid = (xy.mean(axis=0) - points.mean(axis=0)) / scale * 2.0
        return np.concatenate([edge_res, anchor, centroid])

    sol = least_squares(
        residual,
        points.reshape(-1),
        bounds=(lb, ub),
        max_nfev=400,
        xtol=1e-10,
        ftol=1e-10,
        gtol=1e-10,
    )
    xy = sol.x.reshape(n, 2)
    xyz, _, stretch = evaluate_edges(xy, edges, zfun, rest)
    return sol, xy, xyz, rest, stretch, boundary


def node_edge_stats(n_nodes: int, edges: np.ndarray, stretch: np.ndarray):
    values = [[] for _ in range(n_nodes)]
    for value, (i, j) in zip(stretch, edges):
        values[i].append(float(value))
        values[j].append(float(value))
    vmax = np.array([max(v) if v else np.nan for v in values])
    vmean = np.array([np.mean(v) if v else np.nan for v in values])
    return vmax, vmean


def design_candidate(df: pd.DataFrame):
    a0 = CONFIG["current_hex_side_mm"]
    pitch = CONFIG["current_pitch_mm"]
    alpha = CONFIG["compensation_fraction"]
    cap = CONFIG["design_lambda_cap"]
    min_side = CONFIG["min_hex_side_mm"]

    lam = np.clip(df["relaxed_edge_stretch_max"].to_numpy(), 1.0, cap)
    reserve = alpha * pitch * (lam - 1.0)
    current_flat_to_flat = np.sqrt(3.0) * a0
    new_flat_to_flat = current_flat_to_flat - reserve
    side = np.clip(new_flat_to_flat / np.sqrt(3.0), min_side, a0)
    gap = pitch - np.sqrt(3.0) * side
    out = df.copy()
    out["candidate_hex_side_mm"] = side
    out["candidate_ligament_gap_mm"] = gap
    out["candidate_hole_scale"] = side / a0
    return out


def displacement_interpolator(points, displacement):
    linx = LinearNDInterpolator(points, displacement[:, 0], fill_value=np.nan)
    liny = LinearNDInterpolator(points, displacement[:, 1], fill_value=np.nan)
    nearx = NearestNDInterpolator(points, displacement[:, 0])
    neary = NearestNDInterpolator(points, displacement[:, 1])

    def fn(q):
        q = np.atleast_2d(np.asarray(q, float))
        dx = np.asarray(linx(q), float).reshape(-1)
        dy = np.asarray(liny(q), float).reshape(-1)
        missing = np.isnan(dx) | np.isnan(dy)
        if np.any(missing):
            dx[missing] = np.asarray(nearx(q[missing]), float).reshape(-1)
            dy[missing] = np.asarray(neary(q[missing]), float).reshape(-1)
        return np.column_stack([dx, dy])

    return fn


def mapped_cell_lines(cells, zfun, disp_fn=None):
    xs, ys, zs = [], [], []
    for poly in cells:
        q = np.asarray(poly.exterior.coords)
        if disp_fn is not None:
            q = q + disp_fn(q)
        z = zfun(q)
        xs.extend(q[:, 0].tolist() + [None])
        ys.extend(q[:, 1].tolist() + [None])
        zs.extend(z.tolist() + [None])
    return xs, ys, zs


def plot_heatmap(df: pd.DataFrame, output: Path, title: str):
    fig, ax = plt.subplots(figsize=(7, 8))
    values = 100.0 * (df["relaxed_edge_stretch_max"] - 1.0)
    sc = ax.scatter(df["x0_mm"], df["y0_mm"], c=values, s=260)
    ax.set_aspect("equal")
    ax.set_xlabel("X local [mm]")
    ax.set_ylabel("Y local [mm]")
    ax.set_title(title)
    fig.colorbar(sc, ax=ax, label="demanda geométrica efetiva [%]")
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def plot_candidate(df: pd.DataFrame, output: Path, title: str):
    fig, ax = plt.subplots(figsize=(7, 8))
    sc = ax.scatter(df["x0_mm"], df["y0_mm"], c=df["candidate_hex_side_mm"], s=260)
    ax.set_aspect("equal")
    ax.set_xlabel("X local [mm]")
    ax.set_ylabel("Y local [mm]")
    ax.set_title(title)
    fig.colorbar(sc, ax=ax, label="lado sugerido do hexágono [mm]")
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def polygon_path(poly: Polygon, xoff=0.0, yoff=0.0):
    coords = np.asarray(poly.exterior.coords)
    out = [f"M {coords[0,0]+xoff:.3f},{-(coords[0,1]+yoff):.3f}"]
    out += [f"L {x+xoff:.3f},{-(y+yoff):.3f}" for x, y in coords[1:]]
    out.append("Z")
    return " ".join(out)


def write_candidate_svg(outer, cells, df, output: Path, label: str):
    xmin, ymin, xmax, ymax = outer.bounds
    width = xmax - xmin
    height = ymax - ymin
    gap = 20.0
    canvas_w = 2 * width + gap + 20
    canvas_h = height + 30
    shift1x = 10 - xmin
    shift1y = 15
    shift2x = 10 + width + gap - xmin
    shift2y = 15

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w:.1f}mm" height="{canvas_h:.1f}mm" viewBox="0 0 {canvas_w:.1f} {canvas_h:.1f}">',
        '<g fill="none" stroke="black" stroke-width="0.25">',
        f'<path d="{polygon_path(outer, shift1x, shift1y-ymax)}"/>',
        f'<path d="{polygon_path(outer, shift2x, shift2y-ymax)}"/>',
    ]
    for i, poly in enumerate(cells):
        lines.append(f'<path d="{polygon_path(poly, shift1x, shift1y-ymax)}"/>')
        c = np.array([poly.centroid.x, poly.centroid.y])
        scale = float(df.iloc[i]["candidate_hole_scale"])
        coords = np.asarray(poly.exterior.coords)
        scaled = c + (coords - c) * scale
        candidate = Polygon(scaled)
        lines.append(f'<path d="{polygon_path(candidate, shift2x, shift2y-ymax)}"/>')
    lines += [
        '</g>',
        f'<text x="10" y="10" font-size="4">{label} — atual</text>',
        f'<text x="{10+width+gap:.2f}" y="10" font-size="4">{label} — candidato v0.1</text>',
        '</svg>',
    ]
    output.write_text("\n".join(lines), encoding="utf-8")


def make_viewer(pair, df, output: Path):
    tool = pair["tool_mesh"]
    tc = pair["tool_center"]
    v = tool.vertices.copy()
    v[:, :2] -= tc[:2]
    f = tool.faces

    direct_lines = mapped_cell_lines(pair["cells"], pair["zfun"])
    disp_fn = displacement_interpolator(pair["centers"], pair["xy_relaxed"] - pair["centers"])
    relaxed_lines = mapped_cell_lines(pair["cells"], pair["zfun"], disp_fn)

    traces = [
        go.Mesh3d(
            x=v[:, 0], y=v[:, 1], z=v[:, 2],
            i=f[:, 0], j=f[:, 1], k=f[:, 2],
            opacity=0.35, name="ferramenta 3D", hoverinfo="skip"
        ),
        go.Scatter3d(
            x=direct_lines[0], y=direct_lines[1], z=direct_lines[2],
            mode="lines", name="hexágonos — projeção direta", visible=True
        ),
        go.Scatter3d(
            x=pair["p3_direct"][:, 0], y=pair["p3_direct"][:, 1], z=pair["p3_direct"][:, 2],
            mode="markers", name="demanda — projeção direta",
            marker=dict(size=5, color=100*(df["direct_edge_stretch_max"]-1), showscale=True, colorbar=dict(title="%")),
            text=[f"célula {i}<br>max efetivo={100*(s-1):.1f}%" for i,s in enumerate(df["direct_edge_stretch_max"])],
            hovertemplate="%{text}<extra></extra>", visible=True
        ),
        go.Scatter3d(
            x=relaxed_lines[0], y=relaxed_lines[1], z=relaxed_lines[2],
            mode="lines", name="hexágonos — drape relaxado", visible=False
        ),
        go.Scatter3d(
            x=pair["p3_relaxed"][:, 0], y=pair["p3_relaxed"][:, 1], z=pair["p3_relaxed"][:, 2],
            mode="markers", name="demanda — drape relaxado",
            marker=dict(size=5, color=100*(df["relaxed_edge_stretch_max"]-1), showscale=True, colorbar=dict(title="%")),
            text=[f"célula {i}<br>max efetivo={100*(s-1):.1f}%<br>fluxo XY={d:.2f} mm" for i,(s,d) in enumerate(zip(df["relaxed_edge_stretch_max"],df["xy_shift_mm"]))],
            hovertemplate="%{text}<extra></extra>", visible=False
        ),
    ]
    fig = go.Figure(traces)
    fig.update_layout(
        title=pair["label"] + " — conformação geométrica v0.1",
        scene=dict(xaxis_title="X [mm]", yaxis_title="Y [mm]", zaxis_title="Z [mm]", aspectmode="data"),
        updatemenus=[dict(
            buttons=[
                dict(label="Projeção direta", method="update", args=[{"visible": [True, True, True, False, False]}]),
                dict(label="Drape relaxado", method="update", args=[{"visible": [True, False, False, True, True]}]),
            ],
            x=0.01, y=1.08,
        )],
        margin=dict(l=0, r=0, t=70, b=0),
    )
    fig.write_html(output, include_plotlyjs=True)


def analyze(pair_cfg):
    lamp_mesh, lamp_center, cells, outer = extract_cells(pair_cfg["lamp"], CONFIG["section_z_mm"])
    tool_mesh, tool_center, zfun = surface_interpolator(pair_cfg["tool"])
    centers = np.asarray([[p.centroid.x, p.centroid.y] for p in cells])
    edges = build_neighbor_graph(centers)

    direct_xyz, rest, direct_stretch = evaluate_edges(centers, edges, zfun)
    sol, relaxed_xy, relaxed_xyz, _, relaxed_stretch, boundary = relax_drape(
        centers, edges, zfun, tool_mesh, tool_center
    )
    direct_max, direct_mean = node_edge_stats(len(centers), edges, direct_stretch)
    relaxed_max, relaxed_mean = node_edge_stats(len(centers), edges, relaxed_stretch)

    df = pd.DataFrame({
        "cell": np.arange(len(centers)),
        "x0_mm": centers[:, 0],
        "y0_mm": centers[:, 1],
        "z_direct_mm": direct_xyz[:, 2],
        "direct_edge_stretch_max": direct_max,
        "direct_edge_stretch_mean": direct_mean,
        "x_relaxed_mm": relaxed_xy[:, 0],
        "y_relaxed_mm": relaxed_xy[:, 1],
        "z_relaxed_mm": relaxed_xyz[:, 2],
        "relaxed_edge_stretch_max": relaxed_max,
        "relaxed_edge_stretch_mean": relaxed_mean,
        "xy_shift_mm": np.linalg.norm(relaxed_xy - centers, axis=1),
        "boundary_cell": boundary,
    })
    df = design_candidate(df)

    return {
        **pair_cfg,
        "lamp_mesh": lamp_mesh,
        "lamp_center": lamp_center,
        "tool_mesh": tool_mesh,
        "tool_center": tool_center,
        "cells": cells,
        "outer": outer,
        "zfun": zfun,
        "centers": centers,
        "edges": edges,
        "p3_direct": direct_xyz,
        "p3_relaxed": relaxed_xyz,
        "xy_relaxed": relaxed_xy,
        "stretch_direct": direct_stretch,
        "stretch_relaxed": relaxed_stretch,
        "solver": sol,
        "df": df,
    }


def summarize(pair):
    sd = pair["stretch_direct"]
    sr = pair["stretch_relaxed"]
    df = pair["df"]
    return {
        "pair": pair["label"],
        "cells": int(len(df)),
        "neighbor_edges": int(len(pair["edges"])),
        "solver_success": bool(pair["solver"].success),
        "direct_mean_effective_stretch_pct": float(100*(np.mean(sd)-1)),
        "direct_p95_effective_stretch_pct": float(100*(np.percentile(sd,95)-1)),
        "direct_max_effective_stretch_pct": float(100*(np.max(sd)-1)),
        "relaxed_mean_effective_stretch_pct": float(100*(np.mean(sr)-1)),
        "relaxed_p95_effective_stretch_pct": float(100*(np.percentile(sr,95)-1)),
        "relaxed_max_effective_stretch_pct": float(100*(np.max(sr)-1)),
        "mean_xy_feed_mm": float(df["xy_shift_mm"].mean()),
        "max_xy_feed_mm": float(df["xy_shift_mm"].max()),
        "candidate_hex_side_min_mm": float(df["candidate_hex_side_mm"].min()),
        "candidate_hex_side_mean_mm": float(df["candidate_hex_side_mm"].mean()),
        "candidate_ligament_gap_max_mm": float(df["candidate_ligament_gap_mm"].max()),
    }


def main():
    summaries = []
    for cfg in PAIRS:
        pair = analyze(cfg)
        df = pair["df"]
        slug = cfg["slug"]
        df.to_csv(RESULTS / f"{slug}_cells.csv", index=False)
        plot_heatmap(df, RESULTS / f"{slug}_relaxed_demand.png", cfg["label"] + " — demanda após relaxamento")
        plot_candidate(df, RESULTS / f"{slug}_candidate_hex_size.png", cfg["label"] + " — candidato v0.1")
        write_candidate_svg(pair["outer"], pair["cells"], df, RESULTS / f"{slug}_original_vs_candidate.svg", cfg["label"])
        make_viewer(pair, df, RESULTS / f"{slug}_3d_drape.html")
        summaries.append(summarize(pair))

    (RESULTS / "summary.json").write_text(json.dumps({"config": CONFIG, "pairs": summaries}, indent=2), encoding="utf-8")
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
