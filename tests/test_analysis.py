import json
import zipfile
from copy import deepcopy
from types import SimpleNamespace
import numpy as np
import pytest
import trimesh
from shapely.geometry import LineString, Polygon
from analysis.geometry import ROOT, LEGACY, PAIRS, load_part, sha256
from analysis.lattice import assemble_network, wave_path
from analysis.solver import solve_design
from analysis.risk import print_gate, enrich_metrics

CAT=json.loads((ROOT/'dist/data/results.json').read_text(encoding='utf-8'))

@pytest.mark.parametrize('part',['hab2','submerged'])
def test_exported_meshes_rim_and_structural_paths(part):
    spec=next(p for p in PAIRS if p[0]==part); source=load_part(spec)
    for design in CAT['designs']:
        item=design[part]; mesh=trimesh.load_mesh(ROOT/'dist'/item['stl'])
        assert sha256(ROOT/'dist'/item['stl'])==item['validation']['sha256']
        assert np.allclose(mesh.extents,source.mesh.extents,atol=.02)
        if design['id']=='original':
            assert sha256(ROOT/'dist'/item['stl'])==sha256(source.source)
            continue
        assert mesh.is_watertight and mesh.is_winding_consistent and mesh.body_count==1
        assert mesh.nondegenerate_faces().all() and mesh.unique_faces().all()
        mesh.apply_translation([-source.center[0],-source.center[1],0])
        missing=trimesh.boolean.difference([source.rim,mesh],engine='manifold')
        assert abs(missing.volume)<.01
        # Independent containment probes inside the reloaded STL, across every
        # segment: verifies model paths actually have the required material.
        net=json.loads((ROOT/f'generated/sweep/{design["id"]}/{part}_lattice.json').read_text())
        nodes=np.asarray(net['nodes']);edges=np.asarray(net['edges']);points=[]
        for a,b in nodes[edges]:
            direction=b-a;normal=np.array([-direction[1],direction[0]])/np.linalg.norm(direction)
            for t in [.3,.5,.7]:
                for offset in [-.38,0,.38]:points.append([*(a+t*direction+offset*normal),.5])
        assert mesh.contains(np.array(points)).all(),design['id']

def test_risk_and_gates_recomputed_without_score_or_material():
    manufacturing=CAT['manufacturing']
    for design in CAT['designs']:
        for part in ['hab2','submerged']:
            result=json.loads((ROOT/f'generated/sweep/{design["id"]}/{part}_result.json').read_text())
            base=json.loads((ROOT/f'generated/sweep/original/{part}_result.json').read_text())
            result['parent_demand']=np.array(result['parent_demand']);base['parent_demand']=np.array(base['parent_demand'])
            expected=result['metrics']['risk_index'];enrich_metrics(result,base)
            assert result['metrics']['risk_index']==pytest.approx(expected)
            if design['id']!='original':assert print_gate(result,base,manufacturing)==design[part]['gate']
            result['metrics']['material_area_proxy']*=100
            enrich_metrics(result,base);assert result['metrics']['risk_index']==pytest.approx(expected)
            net=json.loads((ROOT/f'generated/sweep/{design["id"]}/{part}_lattice.json').read_text())
            parent=np.array(net['parent']);strain=np.array(result['edge_strain'])
            recomputed=np.array([max(0,strain[parent==p].max()) for p in range(246)])
            assert np.allclose(recomputed,result['parent_demand'])
            assert np.percentile(recomputed,95)==pytest.approx(result['metrics']['p95'])
    accepted=[d for d in CAT['designs'] if d['gate']['passed']]
    winner=min(accepted,key=lambda d:d['combined_risk'])['id'] if accepted else None
    assert CAT['recommendation']['candidate_id']==winner

def test_solver_reacts_to_width_and_curved_paths_have_real_length():
    nodes=np.array([[-2.,0],[0.,0],[2.,0],[0.,2.]])
    edges=np.array([[0,1],[1,2],[1,3]])
    base=dict(nodes=nodes,edges=edges,pitch=3.)
    paths=[nodes[e] for e in edges]
    net=assemble_network(base,paths,np.ones(3),[],1.,1.)
    net['anchor_nodes']=np.array([0,2,3])
    tool=dict(mesh=SimpleNamespace(bounds=np.array([[-5,-5,0],[5,5,3]])),surface=lambda xy:1.8*np.exp(-(xy[:,0]**2+xy[:,1]**2)/4))
    first=solve_design(None,tool,net)
    altered=deepcopy(net);altered['width'][0]=3.
    second=solve_design(None,tool,altered)
    assert np.linalg.norm(first['formed_nodes']-second['formed_nodes'])>.01
    path=wave_path(nodes[0],nodes[2],.6)
    assert np.allclose(path[[0,-1]],nodes[[0,2]])
    assert np.linalg.norm(np.diff(path,axis=0),axis=1).sum()>4

def test_zip_files_and_original_hashes():
    for name,digest in CAT['source_hashes'].items():assert sha256(LEGACY/name)==digest
    for design in CAT['designs']:
        with zipfile.ZipFile(ROOT/'dist'/design['zip']) as archive:
            assert archive.testzip() is None
            assert set(['HAB-2.stl','Sub-Merged.stl','metrics.json','parameters.json','README.txt'])<=set(archive.namelist())
            for part,name in [('hab2','HAB-2.stl'),('submerged','Sub-Merged.stl')]:
                assert archive.read(name)==(ROOT/'dist'/design[part]['stl']).read_bytes()
    if CAT['recommendation']['candidate_id']:
        with zipfile.ZipFile(ROOT/'dist'/CAT['recommendation']['zip']) as archive:
            assert set(['HAB-2_TEST_V1.stl','SubMerged_TEST_V1.stl','parameters.json','metrics.json','comparison.png','risk_map_hab2.png','risk_map_submerged.png','README.txt'])==set(archive.namelist())
