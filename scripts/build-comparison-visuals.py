"""Presentation-only differences between already generated equal-volume solids."""
import json
from pathlib import Path
import numpy as np
import trimesh
root=Path(__file__).resolve().parents[1]
cat=json.loads((root/'dist/data/parametric/catalog.json').read_text(encoding='utf-8'))
def mesh(entry):
    d=json.loads((root/'dist'/entry['data']).read_text(encoding='utf-8'))['lamp']
    return trimesh.Trimesh(np.array(d['positions']).reshape(-1,3),np.array(d['indices']).reshape(-1,3),process=True)
def encode(m):return None if not len(m.faces) else dict(positions=m.vertices.reshape(-1).tolist(),indices=m.faces.reshape(-1).tolist())
out=root/'dist/media/comparisons';out.mkdir(parents=True,exist_ok=True)
for part in ['hab2','submerged']:
    ref=next(e for e in cat['designs'] if e['part']==part and e['id']=='honeycomb_equal');a=mesh(ref)
    for e in cat['designs']:
        if e['part']!=part or not e['parameters']['equal_material']:continue
        if e['id']==ref['id']:value=dict(added=None,removed=None)
        else:
            b=mesh(e);value=dict(added=encode(trimesh.boolean.difference([b,a],engine='manifold')),removed=encode(trimesh.boolean.difference([a,b],engine='manifold')))
        (out/f'{part}-{e["id"]}.json').write_text(json.dumps(value,separators=(',',':')),encoding='utf-8')
