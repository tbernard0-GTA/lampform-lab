import json,zipfile
import numpy as np
from shapely import from_wkt
from shapely.geometry import Polygon
from analysis.geometry import ROOT,sha256
from analysis.local_deformation import affine_fit
from analysis.calibrate_physical import validate_job

def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8-sig'))
def test_causal_candidates_preserve_core_and_isolate_factors():
    c=read('dist/data/physical/results.json');items={d['id']:d for d in c['designs']}
    nets={k:read(f'generated/physical/{k}/submerged/lattice.json') for k in ['test_a','test_b','test_c','test_d']}
    for k in nets:
        assert np.array_equal(np.array(nets[k]['nodes'])[:162],np.array(nets['test_a']['nodes'])[:162])
        assert items[k]['submerged']['validation']['printable_geometry_checks_passed']
        assert sha256(ROOT/'dist'/items[k]['submerged']['stl'])==items[k]['submerged']['validation']['sha256']
    ca=read('generated/physical/test_c/submerged/geometry_checks.json')
    assert ca['core_changed_area_mm2']<1e-7
    for x,y in [('test_a','test_c'),('test_b','test_d')]:
        dx=read('dist/'+items[x]['submerged']['data']);dy=read('dist/'+items[y]['submerged']['data'])
        for a,b in zip(dx['cells'],dy['cells']):assert Polygon(a['candidate']).symmetric_difference(Polygon(b['candidate'])).area<1e-4
    # The reserve factor leaves the 20 boundary contact paths/widths unchanged.
    for x,y in [('test_a','test_b'),('test_c','test_d')]:
        assert nets[x]['parent_paths'][226:]==nets[y]['parent_paths'][226:]
        for net in [nets[x],nets[y]]:assert len(net['parent_paths'])==246
        assert np.allclose(np.array(nets[x]['width'])[np.array(nets[x]['parent'])>=226],np.array(nets[y]['width'])[np.array(nets[y]['parent'])>=226])

def test_actual_local_fits_and_stable_ids():
    catalog=read('dist/data/physical/results.json')
    for d in catalog['designs']:
        for p in ['hab2','submerged']:
            if p not in d:continue
            cells=read('dist/'+d[p]['local_data']);assert len(cells)==65
            assert len(set(c['cell_id'] for c in cells))==65
            for c in cells:
                assert c['lambda1']>=c['lambda2']>0
                assert np.isclose(c['J'],c['lambda1']*c['lambda2'])
                assert np.allclose(np.linalg.svd(c['F'],compute_uv=False),[c['lambda1'],c['lambda2']])

def test_measurement_pack_contains_no_fabricated_measurements():
    import csv,io
    with zipfile.ZipFile(ROOT/'dist/downloads/LAMPFORM_PHYSICAL_TEST_V1.zip') as z:
        assert set(['TEST_A_ORIGINAL.stl','TEST_B_RESERVE.stl','TEST_C_BOUNDARY.stl','TEST_D_HYBRID.stl','predictions.json','test_procedure.md','cell_reference_map.svg','measurement_plan.svg']).issubset(z.namelist())
        rows=list(csv.DictReader(io.StringIO(z.read('experiment_template.csv').decode())))
        assert len(rows)==80 and all(not r['L1_after_mm'] and not r['failure'] for r in rows)
    plans=read('dist/data/physical/measurement_plan.json');assert all(len(set(v))==20 for v in plans.values())

def test_calibration_rejects_leakage_and_missing_measurements():
    import pytest
    r=dict(experiment_id='E',sample_id='A',part='submerged',design='original',cell_id='S001',L1_before_mm='',L1_after_mm='')
    with pytest.raises(ValueError):validate_job(dict(calibration=[r]*5,validation=[r]*5))
