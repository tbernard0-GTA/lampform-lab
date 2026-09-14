import json, zipfile
import numpy as np
import trimesh
from analysis.geometry import ROOT, sha256

def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
CAT=read('dist/data/parametric/catalog.json')

def test_catalog_export_integrity_and_actual_solver_sections():
    assert len(CAT['designs'])==48
    for e in CAT['designs']:
        mesh=trimesh.load_mesh(ROOT/'dist'/e['stl'],process=True)
        assert mesh.is_watertight and mesh.body_count==1
        assert mesh.nondegenerate_faces().all() and mesh.unique_faces().all()
        assert sha256(ROOT/'dist'/e['stl'])==e['validation']['sha256']
        assert e['solver_converged'] and e['validation']['missing_rim_mm3']<.01
        net=read(f'generated/parametric/{e["part"]}/{e["id"]}/network.json')
        w=np.array(net['width']);h=np.array(net['height']);length=np.array(net['rest_length'])
        assert np.allclose(h/.1,np.round(h/.1))
        assert w.min()>=.8-1e-8 and w.max()<=1.6+1e-8
        assert h.min()>=.8-1e-8 and h.max()<=2+1e-8
        assert np.allclose(net['area_mm2'],w*h)
        assert np.allclose(net['axial_stiffness_proxy'],w*h/length)
        assert np.allclose(net['I_in_plane_mm4'],h*w**3/12)
        assert np.allclose(net['I_out_plane_mm4'],w*h**3/12)
        data=read('dist/'+e['data'])
        assert len(data['vertex_edges'])==len(data['lamp']['positions'])//3
        assert all(np.isfinite([c['lambda1'],c['lambda2'],c['area'],c['demand']]).all() for c in data['cells'])

def test_doe_isolates_width_height_with_comparable_actual_budgets():
    for part in ['hab2','submerged']:
        entries={e['id']:e for e in CAT['designs'] if e['part']==part}
        nets={k:read(f'generated/parametric/{part}/{k}/network.json') for k in CAT['doe']}
        for k,n in nets.items():
            assert np.array_equal(np.array(n['nodes'])[:182],np.array(nets['A_uniform']['nodes'])[:182])
            assert n['anchor_nodes']==nets['A_uniform']['anchor_nodes']
            edges=np.array(n['edges']);h=np.array(n['height']);w=np.array(n['width'])
            for node in range(len(n['nodes'])):
                mask=(edges==node).any(axis=1)
                assert np.ptp(h[mask])<=.200001 and np.ptp(w[mask])<=.200001
        assert np.ptp(nets['B_width']['width'])>.01 and np.ptp(nets['B_width']['height'])==0
        assert np.ptp(nets['C_height']['height'])>.09 and np.ptp(nets['C_height']['width'])==0
        for k in ['B_width','C_height','D_both']:
            assert 9.8<entries[k]['metrics']['material_delta_pct']<10.1
        fair=[entries[k]['metrics']['lattice_volume_mm3'] for k in CAT['equal_material_ids']]
        assert np.ptp(fair)/np.mean(fair)<.005
        # Height changes feed into an actual, different solve, not only rendering.
        assert abs(entries['C_height']['metrics']['p95']-entries['A_uniform']['metrics']['p95'])>.1

def test_v2_pack_matches_exact_stls_and_preserves_v06():
    with zipfile.ZipFile(ROOT/'dist/downloads/LAMPFORM_PARAMETRIC_TEST_V2.zip') as z:
        for e in CAT['designs']:
            if e['id'] in CAT['doe']:
                assert z.read(e['part']+'/'+e['id']+'.stl')==(ROOT/'dist'/e['stl']).read_bytes()
        for part in ['hab2','submerged']:
            for f in ['parameters.json','predictions.json','comparison.png','width_map.png','height_map.png','README.md']:
                assert part+'/'+f in z.namelist()
    assert read('dist/data/physical/results.json')['version']=='0.6.0'
