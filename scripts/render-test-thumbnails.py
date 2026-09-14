"""Render existing v0.8 solids; no geometry generation or solver execution."""
import json, hashlib
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
ROOT=Path(__file__).resolve().parents[1]
catalog=json.loads((ROOT/'dist/data/parametric/catalog.json').read_text(encoding='utf-8'))
out=ROOT/'dist/media/tests';out.mkdir(parents=True,exist_ok=True)
for e in catalog['designs']:
    d=json.loads((ROOT/'dist'/e['data']).read_text(encoding='utf-8'));v=np.array(d['lamp']['positions']).reshape(-1,3);f=np.array(d['lamp']['indices']).reshape(-1,3)
    triangles=v[f];normals=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-10)
    light=np.array([-.3,-.6,.74]);light/=np.linalg.norm(light);shade=.60+.40*np.maximum(0,normals@light);base=np.array([.66,.73,.59]);colors=np.clip(shade[:,None]*base,0,1)
    fig=plt.figure(figsize=(7,4.8),facecolor='#edf0e7');ax=fig.add_axes([0,0,1,1],projection='3d',computed_zorder=False);ax.set_facecolor('#edf0e7')
    ax.add_collection3d(Poly3DCollection(triangles,facecolors=colors,edgecolors='none',linewidths=0,rasterized=True))
    ax.set(xlim=(-42,42),ylim=(-54,54),zlim=(-15,15));ax.set_box_aspect((84,108,30),zoom=1.4);ax.view_init(elev=28,azim=-62);ax.set_proj_type('ortho');ax.set_axis_off()
    fig.savefig(out/f'{"peca-1" if e["part"]=="hab2" else "peca-2"}-{e["id"]}.png',dpi=130);plt.close(fig)
    print(e['part'],e['id'],flush=True)
