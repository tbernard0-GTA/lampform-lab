"""Generate exact v0.8 catalogue; never interpolate solver metrics."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import sys,json,hashlib,argparse
from pathlib import Path
if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import trimesh
from shapely.geometry import Polygon
from shapely.ops import unary_union
from analysis.geometry import ROOT,PAIRS,load_part,load_tool,mesh_json,sha256
from analysis.parametric_geometry import topology,build_geometry,field_values,network,profiles,projected_volume,export,cells,LIMITS
from analysis.parametric_solver import solve_design
from analysis.run_design_sweep import write_json,serializable

def configs():
    base=dict(topology='honeycomb',pitch_mm=8.,base_width_mm=1.,base_height_mm=1.,orientation_deg=0.,adaptation='uniform',response='reinforce',width_response=0.,height_response=0.,material_budget_pct=0.,equal_material=False)
    out=[]
    def add(id,name,**changes):out.append(dict(id=id,name=name,**{**base,**changes}))
    add('A_uniform','A · Uniform')
    for w in [.8,1.,1.2]:
        for h in [.8,1.,1.2]:
            if w==h==1:continue
            add(f'uniform_w{int(w*10)}_h{int(h*10)}',f'Uniform · {w:g} × {h:g} mm',base_width_mm=w,base_height_mm=h)
    add('B_width','B · Width adaptive',adaptation='adaptive',width_response=1.,material_budget_pct=10.)
    add('C_height','C · Height adaptive',adaptation='adaptive',height_response=1.,material_budget_pct=10.)
    add('D_both','D · Width + height',adaptation='adaptive',width_response=1.,height_response=1.,material_budget_pct=10.)
    add('width_half','Width response · 50%',adaptation='adaptive',width_response=.5,material_budget_pct=10.)
    add('height_half','Height response · 50%',adaptation='adaptive',height_response=.5,material_budget_pct=10.)
    add('both_budget20','Width + height · budget 20%',adaptation='adaptive',width_response=1.,height_response=1.,material_budget_pct=20.)
    add('comply','Comply · reduced section',adaptation='adaptive',response='comply',width_response=1.,height_response=1.)
    add('mechanism','Mechanism-aware',adaptation='mechanism',response='mechanism',width_response=1.,height_response=1.,material_budget_pct=10.)
    add('honey_pitch10','Honeycomb · pitch 10',pitch_mm=10.)
    for kind in ['triangle','diamond']:
        add(kind+'_uniform',kind.title()+' · Uniform',topology=kind)
    for kind in ['honeycomb','triangle','diamond']:
        add(kind+'_equal',kind.title()+' · Equal volume',topology=kind,equal_material=True)
    add('diamond_rotated','Diamond · rotated 30°',topology='diamond',orientation_deg=30.)
    return out

def compact(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':'),default=serializable,allow_nan=False),encoding='utf-8')

def vertex_parents(mesh,net):
    a=net['nodes'][net['edges'][:,0]];b=net['nodes'][net['edges'][:,1]];delta=b-a;length2=(delta**2).sum(axis=1);out=[]
    for chunk in np.array_split(mesh.vertices[:,:2],max(1,len(mesh.vertices)//300)):
        t=np.clip(((chunk[:,None]-a)*delta).sum(axis=2)/length2,0,1)
        d=((chunk[:,None]-a-t[:,:,None]*delta)**2).sum(axis=2);idx=np.argmin(d,axis=1);idx[np.min(d,axis=1)>(net['width'][idx]/2+.05)**2]=-1;out.extend(idx.tolist())
    return out

def main(args):
    catalog=dict(version='0.8.0',status='UNCALIBRATED · NO PHYSICAL VALIDATION DATA YET',limits=LIMITS,designs=[],doe=['A_uniform','B_width','C_height','D_both'],equal_material_ids=['honeycomb_equal','triangle_equal','diamond_equal'])
    fingerprint={p:sha256(ROOT/'analysis'/p) for p in ['parametric_geometry.py','parametric_solver.py']}
    for spec in PAIRS:
        if args.part and args.part!=spec[0]:continue
        part=load_part(spec);tool=load_tool(spec);source=json.loads((ROOT/f'dist/data/physical/original/{part.id}_cells.json').read_text())
        compact(ROOT/f'dist/data/parametric/tool_{part.id}.json',mesh_json(tool['mesh']))
        graphs={}
        def graph(c):
            key=(c['topology'],c['pitch_mm'],c['orientation_deg'])
            if key not in graphs:graphs[key]=topology(part,*key)
            return graphs[key]
        original_cfg=configs()[0];g=graph(original_cfg);_,_,_,base_volume=build_geometry(part,g,source,original_cfg)
        min_volumes=[];max_volumes=[]
        for kind in ['honeycomb','triangle','diamond']:
            cfg={**original_cfg,'topology':kind,'base_width_mm':.8};min_volumes.append(build_geometry(part,graph(cfg),source,cfg)[3]);cfg['base_width_mm']=1.6;max_volumes.append(build_geometry(part,graph(cfg),source,cfg)[3])
        fair_volume=max(min_volumes)*1.015
        if fair_volume>min(max_volumes):raise ValueError('No equal-volume feasible interval under manufacturing limits')
        original_mesh=None;original_result=None
        for index,cfg in enumerate(configs()):
            if args.limit and index>=args.limit:break
            print(part.id,cfg['id'],'generate',flush=True);g=graph(cfg)
            if cfg['equal_material']:
                lo=.8;hi=1.6
                for _ in range(18):
                    mid=(lo+hi)/2;cfg['base_width_mm']=mid;vol=build_geometry(part,g,source,cfg)[3]
                    if vol<fair_volume:lo=mid
                    else:hi=mid
                cfg['base_width_mm']=(lo+hi)/2
            cfg['target_lattice_volume_mm3']=fair_volume if cfg['equal_material'] else base_volume*(1+cfg['material_budget_pct']/100)
            fields,net,layers,volume=build_geometry(part,g,source,cfg,cfg['target_lattice_volume_mm3'])
            folder=ROOT/f'generated/parametric/{part.id}/{cfg["id"]}';folder.mkdir(parents=True,exist_ok=True)
            stl=f'downloads/parametric/{part.id}/{cfg["id"]}.stl';mesh,validation=export(part,layers,ROOT/'dist'/stl)
            key=hashlib.sha256(json.dumps(dict(cfg=cfg,fingerprint=fingerprint,net=net),default=serializable,sort_keys=True).encode()).hexdigest()
            cache=folder/'result.json'
            if cache.exists() and json.loads(cache.read_text()).get('input_hash')==key:
                result=json.loads(cache.read_text());
                for k in ['nodes','edges','formed_nodes','stage_positions','edge_strain','parent_demand']:result[k]=np.array(result[k])
            else:
                print('  solve',len(net['nodes']),'nodes',flush=True);result=solve_design(part,tool,net)
                if not result['solver']['success']:
                    print('  retry convergence with larger evaluation limit',flush=True);result=solve_design(part,tool,net,dict(max_nfev=1000,tolerance=1e-6))
                result['input_hash']=key;write_json(cache,result)
            if cfg['id']=='A_uniform':original_mesh=mesh;original_result=result;base_actual_volume=float(mesh.volume-part.rim.volume)
            local=cells(g,result,fields)
            footprint=unary_union(list(layers.values()));envelope=Polygon(part.rim_polygon.exterior)
            lattice_volume=float(mesh.volume-part.rim.volume);m=result['metrics'];m.update(material_volume_mm3=float(mesh.volume),lattice_volume_mm3=lattice_volume,
                material_delta_pct=100*(lattice_volume/base_actual_volume-1),open_area=100*(envelope.area-footprint.union(part.rim_polygon).area)/envelope.area,
                minimum_feature_mm=float(net['width'].min()),minimum_height_mm=float(net['height'].min()),maximum_height_mm=float(net['height'].max()),
                predicted_budget_error_pct=100*(lattice_volume/cfg['target_lattice_volume_mm3']-1))
            if cfg['id']=='A_uniform':added=removed=None
            else:
                added=trimesh.boolean.difference([mesh,original_mesh],engine='manifold');removed=trimesh.boolean.difference([original_mesh,mesh],engine='manifold')
            edges=[]
            for i,((a,b),w,h,p) in enumerate(zip(net['edges'],net['width'],net['height'],net['parent'])):
                edges.append(dict(flat=np.r_[net['nodes'][a],0,net['nodes'][b],0].tolist(),stages=[s[[a,b]].reshape(-1).tolist() for s in result['stage_positions']],parent=int(p),width=float(w),height=float(h),area=float(w*h),demand=float(result['parent_demand'][p]),I_in_plane=float(h*w**3/12),I_out_plane=float(w*h**3/12)))
            data=dict(id=cfg['id'],part=part.id,parameters=cfg,metrics=m,validation=validation,solver=result['solver'],lamp=mesh_json(mesh),vertex_edges=vertex_parents(mesh,net),edges=edges,cells=local,
                added=mesh_json(added) if added is not None and len(added.faces) else None,removed=mesh_json(removed) if removed is not None and len(removed.faces) else None)
            data_path=f'data/parametric/{part.id}/{cfg["id"]}.json';compact(ROOT/'dist'/data_path,data);write_json(folder/'parameters.json',cfg);write_json(folder/'network.json',net)
            entry=dict(id=cfg['id'],part=part.id,name=cfg['name'],parameters=cfg,data=data_path,stl=stl,metrics=m,validation=validation,solver_converged=result['solver']['success'],node_count=len(net['nodes']),cell_count=len(local))
            catalog['designs'].append(entry)
            print('  P95',round(m['p95'],2),'height',sorted(layers),'material',round(m['material_delta_pct'],2),'converged',result['solver']['success'],flush=True)
            compact(ROOT/'artifacts/parametric-catalog.partial.json',catalog)
    if not args.limit and not args.part:
        compact(ROOT/'dist/data/parametric/catalog.json',catalog)
        from analysis.parametric_pack import build_packs
        build_packs(catalog)
    else:compact(ROOT/'artifacts/parametric-trial-catalog.json',catalog)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--part');p.add_argument('--limit',type=int);main(p.parse_args())
