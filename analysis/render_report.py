"""Deterministic figures from exported STL sections and solver data."""
import json
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .geometry import ROOT


def render_report(catalog):
    folder = ROOT / 'docs/figures'; folder.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 4, figsize=(14, 10), layout='constrained')
    for col, design in enumerate(catalog['designs']):
        for row, part in enumerate(['hab2', 'submerged']):
            ax = axes[row, col]
            mesh = trimesh.load_mesh(ROOT / 'dist' / design[part]['stl'])
            section = mesh.section(plane_origin=[0, 0, .5], plane_normal=[0, 0, 1])
            for curve in section.discrete:
                ax.plot(curve[:, 0], curve[:, 1], color='#335644', lw=.65)
            ax.set_aspect('equal'); ax.axis('off')
            m = design[part]['metrics']
            ax.set_title(f'{design["name"].replace(" + ", " +\n")}\n{part} · P95 {m["p95"]:.1f}% · max {m["maximum"]:.1f}%', fontsize=10)
    fig.suptitle('LampForm Lab v0.4 — sections of the eight exported STL at z = 0.5 mm', fontsize=14)
    fig.savefig(folder / 'stl-sections.png', dpi=150); plt.close(fig)
    fig, axes = plt.subplots(2, 4, figsize=(14, 10), layout='constrained')
    for col, design in enumerate(catalog['designs']):
        for row, part in enumerate(['hab2', 'submerged']):
            ax = axes[row, col]
            data = json.loads((ROOT / 'dist' / design[part]['data']).read_text(encoding='utf-8'))
            for edge in data['edges']:
                xy = np.array(edge['flat']).reshape(2, 3)
                ax.plot(xy[:, 0], xy[:, 1], color=plt.cm.viridis(np.clip(edge['demand']/180, 0, 1)), lw=1.5)
            ax.set_aspect('equal'); ax.axis('off'); ax.set_title(f'{design["id"]} / {part}', fontsize=10)
    bar = fig.colorbar(plt.cm.ScalarMappable(norm=plt.Normalize(0, 180), cmap='viridis'), ax=axes.ravel().tolist(), shrink=.7)
    bar.set_label('Positive relative demand (%) — common scale; not calibrated strain')
    fig.savefig(folder / 'demand-comparison.png', dpi=150); plt.close(fig)
