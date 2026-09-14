"""Export supplied research for the viewer, without changing or rerunning the solver."""
import csv
import hashlib
import json
import shutil
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'legacy' / 'lampform_lab_v01'
DEST = ROOT / 'dist' / 'data'


def mesh_data(path):
    data = path.read_bytes()
    count = struct.unpack_from('<I', data, 80)[0]
    if len(data) != 84 + 50 * count:
        raise ValueError(f'Unexpected binary STL length: {path}')
    lookup, vertices, faces = {}, [], []
    for i in range(count):
        triangle = struct.unpack_from('<12fH', data, 84 + i * 50)[3:12]
        for j in range(0, 9, 3):
            vertex = triangle[j:j + 3]
            if vertex not in lookup:
                lookup[vertex] = len(vertices)
                vertices.append(vertex)
            faces.append(lookup[vertex])
    low = [min(v[i] for v in vertices) for i in range(3)]
    high = [max(v[i] for v in vertices) for i in range(3)]
    center = [(low[i] + high[i]) / 2 for i in range(2)] + [0]
    return dict(positions=[round(v[i] - center[i], 5) for v in vertices for i in range(3)],
                indices=faces, dimensions=[round(high[i] - low[i], 2) for i in range(3)],
                file=path.name, sha256=hashlib.sha256(data).hexdigest())


def read_csv(path):
    with path.open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    summary = json.loads((SOURCE / 'results_v02' / 'summary_v02.json').read_text())
    slugs = ['hab2_mold', 'submerged_push']
    filenames = [('obj_1_HAB-2.stl', 'obj_2_Mold.stl'),
                 ('obj_3_Sub-merged body.stl', 'obj_4_Push.stl')]
    for i, (slug, files) in enumerate(zip(slugs, filenames)):
        edges = []
        for r in read_csv(SOURCE / 'results_v02' / f'{slug}_ligaments.csv'):
            edges.append(dict(flat=[float(r[f'{axis}_{end}_flat_mm']) if axis != 'z' else 0
                                    for end in ('i', 'j') for axis in ('x', 'y', 'z')],
                              formed=[float(r[f'{axis}_{end}_relaxed_mm'])
                                      for end in ('i', 'j') for axis in ('x', 'y', 'z')],
                              demand=float(r['relaxed_strain_pct'])))
        sensitivity = [{k: float(v) for k, v in r.items()} for r in
                       read_csv(SOURCE / 'results_v02' / f'{slug}_boundary_sensitivity.csv')]
        result = dict(summary=summary[i], lamp=mesh_data(SOURCE / files[0]),
                      tool=mesh_data(SOURCE / files[1]), edges=edges, sensitivity=sensitivity)
        (DEST / f'{slug}.json').write_text(json.dumps(result, separators=(',', ':')), encoding='utf-8')
    (DEST / 'summary_v02.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print('Exported two pairs, four original meshes and the recorded v0.2 results.')


if __name__ == '__main__':
    main()
