"""v0.6, independent of the preserved v0.5 design space. No physical data generated."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import sys,json,copy
from pathlib import Path
if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from analysis.geometry import ROOT,PAIRS,load_part,load_tool,rim_contacts,sha256
from analysis.lattice import base_network
from analysis.local_deformation import analyze_cells,MECHANISM_RULES
from analysis.physical_candidates import physical_design
from analysis.solver import solve_design
from analysis.export_stl import export_design,manufacturing_metrics
from analysis.run_design_sweep import write_json,export_data
from analysis.risk import enrich_metrics
from analysis.scoring import score

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def geometry_delta(original,candidate):
    def path(shape):
        polys=shape.geoms if hasattr(shape,'geoms') else [shape]
        return ' '.join('M'+' L'.join(f'{x:.5f},{-y:.5f}' for x,y in ring.coords)+' Z' for poly in polys if poly.geom_type=='Polygon' and poly.area>1e-8 for ring in [poly.exterior,*poly.interiors])
    added=candidate.difference(original);removed=original.difference(candidate);delta=added.union(removed)
    return dict(added_svg=path(added),removed_svg=path(removed),bounds=list(delta.bounds) if not delta.is_empty else None)
def arrays(r):
    for k in ['nodes','edges','formed_nodes','parent_demand','edge_strain','displacement']:r[k]=np.array(r[k])
    r['stage_positions']=[np.array(x) for x in r['stage_positions']]
    return r

def main():
    old=read(ROOT/'dist/data/results.json');catalog=copy.deepcopy(old)
    catalog.update(version='0.6.0',physical_data_status='NO PHYSICAL VALIDATION DATA YET',mechanism_rules=MECHANISM_RULES)
    catalog['designs']=copy.deepcopy(old['designs']);catalog['causal_tests']=[]
    for spec in PAIRS:
        part=load_part(spec);base=base_network(part.centers);tool=load_tool(spec);contacts=rim_contacts(part,base['nodes'],base['boundary'])
        baseline=arrays(read(ROOT/f'generated/sweep/original/{part.id}_result.json'))
        sensitivity_path=ROOT/f'generated/physical/sensitivity_{part.id}.json'
        if sensitivity_path.exists():sensitivity=arrays(read(sensitivity_path))
        else:
            net=read(ROOT/f'generated/sweep/original/{part.id}_lattice.json')
            for k in ['nodes','edges','width','rest_length','anchor_nodes','parent']:net[k]=np.asarray(net[k])
            sensitivity=solve_design(part,tool,net,dict(boundary_anchor=1.))
            write_json(sensitivity_path,sensitivity)
        for item in catalog['designs'][:len(old['designs'])]:
            r=read(ROOT/f'generated/sweep/{item["id"]}/{part.id}_result.json')
            cells=analyze_cells(part,base,r,sensitivity if item['id']=='original' else None)
            path=f'data/physical/{item["id"]}/{part.id}_cells.json';write_json(ROOT/'dist'/path,cells);item[part.id]['local_data']=path
        original_local=read(ROOT/'dist'/catalog['designs'][0][part.id]['local_data'])
        kinds=['test_a','test_b','test_c','test_d','directional','area'] if part.id=='submerged' else ['test_a']
        for kind in kinds:
            folder=ROOT/f'generated/physical/{kind}/{part.id}';out=ROOT/f'dist/downloads/physical/{kind}/{part.id}';out.mkdir(parents=True,exist_ok=True)
            print(part.id,kind,'geometry',flush=True)
            d=physical_design(part,base,contacts,kind,baseline,original_local)
            mesh,validation=export_design(part,d,out/f'{part.name}.stl')
            cached=folder/'result.json'
            fingerprint={n:sha256(ROOT/'analysis'/n) for n in ['physical_candidates.py','solver.py','local_deformation.py']}
            if cached.exists() and read(cached).get('fingerprint')==fingerprint and read(cached).get('validation',{}).get('sha256')==validation['sha256']:
                result=arrays(read(cached))
            elif kind=='test_a':result=copy.deepcopy(baseline)
            else:result=solve_design(part,tool,d['lattice'])
            result['metrics'].update(manufacturing_metrics(part,d,mesh));enrich_metrics(result,baseline)
            result.update(validation=validation,fingerprint=fingerprint,score=score(result['metrics'],baseline['metrics']))
            m=result['metrics'];m['material_change_pct']=100*(m['material_area_proxy']/baseline['metrics']['material_area_proxy']-1)
            m['geometry_change_pct']=100*d['material'].symmetric_difference(part.lattice_polygon).area/d['material'].union(part.lattice_polygon).area
            dataset=f'data/physical/{kind}/{part.id}.json';export_data(part,tool,d,result,mesh,ROOT/'dist'/dataset)
            data=read(ROOT/'dist'/dataset)
            data['geometry_delta']=geometry_delta(part.lattice_polygon.union(part.rim_polygon),d['material'].union(part.rim_polygon))
            for k,e in enumerate(data['edges']):
                p=e['parent'];a,b=d['lattice']['edges'][k]
                e.update(parent_demand=float(result['parent_demand'][p]),baseline_demand=float(baseline['parent_demand'][p]),
                    delta=float(result['parent_demand'][p]-baseline['parent_demand'][p]),
                    stages=[s[[a,b]].reshape(-1).tolist() for s in result['stage_positions']],
                    xy_feed=float(np.linalg.norm(result['formed_nodes'][[a,b],:2]-result['nodes'][[a,b]],axis=1).mean()))
            write_json(ROOT/'dist'/dataset,data)
            cells=analyze_cells(part,base,result,sensitivity if kind=='test_a' else None)
            local_path=f'data/physical/{kind}/{part.id}_cells.json';write_json(ROOT/'dist'/local_path,cells)
            write_json(folder/'result.json',result);write_json(folder/'lattice.json',d['lattice']);write_json(folder/'geometry_checks.json',d['causal'])
            names=dict(test_a='A · Original repaired',test_b='B · Reserve only',test_c='C · Boundary only',test_d='D · Reserve + Boundary',directional='Directional S reserve',area='Bidirectional undulating cell')
            entry=next((i for i in catalog['designs'] if i['id']==kind),None)
            if entry is None:entry=dict(id=kind,name=names[kind],family='physical',parameters=d['parameters']);catalog['designs'].append(entry)
            entry[part.id]=dict(data=dataset,local_data=local_path,stl=f'downloads/physical/{kind}/{part.id}/{part.name}.stl',metrics=m,validation=validation,solver=result['solver'],causal={k:v for k,v in d['causal'].items() if k!='core_mask'},gate=dict(passed=False,status='EXPERIMENT'))
            if part.id=='submerged' and kind.startswith('test_'):catalog['causal_tests'].append(kind)
            print('  P95',round(m['p95'],2),'core area change',round(d['causal']['core_changed_area_mm2'],8),'solver',result['solver']['success'],flush=True)
    catalog['independent_choices']={p:min((i for i in catalog['designs'] if p in i and i[p].get('gate',{}).get('passed')),key=lambda i:i[p]['metrics']['risk_index'])['id'] for p in ['hab2','submerged']}
    write_json(ROOT/'dist/data/physical/results.json',catalog)
    from analysis.physical_pack import build_pack
    build_pack(catalog)

if __name__=='__main__':main()



