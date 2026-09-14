"""Bounded topology and section fields for v0.8; old pipelines stay unchanged."""
from copy import deepcopy
import numpy as np
import trimesh
import manifold3d
from shapely.geometry import Polygon,LineString,Point
from shapely.ops import unary_union,polygonize,nearest_points
from shapely.affinity import rotate
from shapely import set_precision
from analysis.geometry import rim_contacts,mesh_json,sha256
from analysis.lattice import base_network
from analysis.local_deformation import affine_fit,mechanism

LIMITS=dict(min_width_mm=.8,max_width_mm=1.6,min_height_mm=.8,max_height_mm=2.,
    layer_quantum_mm=.1,transition_radius_mm=12.,max_neighbor_height_step_mm=.2,
    max_neighbor_width_step_mm=.2,gamma=1.3)

def topology(part,kind='honeycomb',pitch=8.,orientation=0.):
    domain=max([Polygon(r) for r in part.rim_polygon.interiors],key=lambda p:p.area)
    if kind=='honeycomb' and pitch==8 and orientation==0:
        base=base_network(part.centers);nodes=base['nodes'].tolist();edges=base['edges'].tolist();anchors=[]
        for c in rim_contacts(part,base['nodes'],base['boundary']):
            edges.append([c['node'],len(nodes)]);anchors.append(len(nodes));nodes.append(c['end'].tolist())
        polygons=part.cells
        cell_nodes=[np.unique(base['edges'][es]).tolist() for es in base['cell_edges']]
    else:
        lines=[]
        if kind=='honeycomb':
            side=pitch/np.sqrt(3);offsets=np.c_[np.cos(np.deg2rad(np.arange(30,390,60))),np.sin(np.deg2rad(np.arange(30,390,60)))]*side
            for row in range(-14,15):
                for col in range(-14,15):
                    center=np.array([pitch*(col+(row%2)/2),row*1.5*side]);poly=Polygon(center+offsets)
                    lines.append(rotate(poly.boundary,orientation,origin=(0,0)))
        else:
            angles=[0,60,120] if kind=='triangle' else [45,135]
            spacing=pitch*np.sqrt(3)/2 if kind=='triangle' else pitch
            for angle in angles:
                for j in range(-25,26):lines.append(rotate(LineString([(-180,j*spacing),(180,j*spacing)]),angle+orientation,origin=(0,0)))
        network=unary_union(lines).intersection(domain.buffer(.3));segments=[]
        for line in network.geoms:
            if line.geom_type!='LineString':continue
            for a,b in zip(line.coords,list(line.coords)[1:]):
                if np.linalg.norm(np.array(a)-b)>.15:segments.append(LineString([a,b]))
        # Remove numerical duplicate intersections before assigning graph IDs.
        lookup={};nodes=[];edges=[]
        def index(p):
            key=tuple(np.round(p,5))
            if key not in lookup:lookup[key]=len(nodes);nodes.append(list(key))
            return lookup[key]
        for line in segments:
            ids=[index(p) for p in line.coords]
            if ids[0]!=ids[1]:edges.append(ids)
        edges=sorted(set(tuple(sorted(e)) for e in edges));nodes=np.array(nodes)
        anchors=[i for i,p in enumerate(nodes) if Point(p).distance(domain.boundary)<.4]
        polygons=sorted([p for p in polygonize([LineString(nodes[e]) for e in np.array(edges)]) if p.area>2],key=lambda p:(p.centroid.y,p.centroid.x))
        cell_nodes=[[int(np.argmin(np.linalg.norm(nodes-np.array(q),axis=1))) for q in list(p.exterior.coords)[:-1]] for p in polygons]
        base=dict(pitch=pitch)
    nodes=np.asarray(nodes,float);edges=np.asarray(edges,int)
    if len(anchors)<6 or not polygons:raise ValueError('Insufficient connected topology or cells')
    return dict(nodes=nodes,edges=edges,anchors=np.array(anchors),polygons=polygons,cell_nodes=cell_nodes,pitch=pitch,kind=kind)

def field_values(graph,source_cells,config,scale=1.):
    p=(graph['nodes'][graph['edges']].mean(axis=1));centers=np.array([c['center'] for c in source_cells]);dist=np.linalg.norm(p[:,None]-centers[None,:],axis=2)
    kernel=np.exp(-.5*(dist/LIMITS['transition_radius_mm'])**2);kernel/=kernel.sum(axis=1)[:,None]
    demand=kernel@np.array([c['demand'] for c in source_cells]);den=max(np.percentile(demand,95)-np.percentile(demand,5),1e-6)
    d=np.clip((demand-np.percentile(demand,5))/den,0,1)**LIMITS['gamma']
    near=np.argmin(dist,axis=1);cats=[source_cells[i]['mechanism'] for i in near]
    w0=config['base_width_mm'];h0=config['base_height_mm'];wg=config.get('width_response',0)*.6;hg=config.get('height_response',0)
    if config['adaptation']=='uniform':wg=hg=0
    ws=np.ones(len(p));hs=np.ones(len(p))
    if config.get('response')=='comply':ws[:]=-.33;hs[:]=-.2
    if config['adaptation']=='mechanism' or config.get('response')=='mechanism':
        for i,j in enumerate(near):
            c=source_cells[j]
            if c['boundary'] and c['xy_feed']>2:ws[i]=-.33;hs[i]=-.1
            elif c['anisotropy']>1.15:ws[i]=-.33;hs[i]=.2
            elif c['J']>1.2:ws[i]=.2;hs[i]=.5
    w=np.clip(w0+scale*wg*d*ws,.8,1.6);h=np.clip(h0+scale*hg*d*hs,.8,2)
    incident=[[] for _ in graph['nodes']]
    for i,e in enumerate(graph['edges']):
        for n in e:incident[n].append(i)
    # Monotonic envelope smoothing enforces a real bound at every junction.
    for values,step in [(w,.2),(h,.2)]:
        for _ in range(20):
            before=values.copy()
            for ids in incident:
                if ids:values[ids]=np.minimum(values[ids],values[ids].min()+step)
            if np.max(abs(values-before))<1e-9:break
    h=np.round(h/.1)*.1
    return dict(width=w,height=h,demand=d,mechanism=cats,incident=incident)

def network(graph,fields):
    nodes=graph['nodes'].tolist();edges=[];width=[];height=[];parent=[];paths=[];node_h=np.array([max(fields['height'][es]) if es else 1. for es in fields['incident']])
    for i,(a,b) in enumerate(graph['edges']):
        p=graph['nodes'][a];q=graph['nodes'][b]
        if node_h[a]==fields['height'][i]==node_h[b]:
            path=np.array([p,q]);ids=[int(a),int(b)];heights=[fields['height'][i]]
        else:
            path=np.array([p,p+.2*(q-p),p+.8*(q-p),q]);ids=[int(a),len(nodes),len(nodes)+1,int(b)];nodes.extend(path[1:-1].tolist());heights=[node_h[a],fields['height'][i],node_h[b]]
        paths.append(path.tolist())
        for j,h in enumerate(heights):edges.append(ids[j:j+2]);width.append(fields['width'][i]);height.append(h);parent.append(i)
    nodes=np.array(nodes);edges=np.array(edges);width=np.array(width);height=np.array(height);length=np.linalg.norm(nodes[edges[:,0]]-nodes[edges[:,1]],axis=1)
    area=width*height;ip=height*width**3/12;op=width*height**3/12
    return dict(nodes=nodes,edges=edges,width=width,thickness=height,height=height,area_mm2=area,
        I_in_plane_mm4=ip,I_out_plane_mm4=op,axial_stiffness_proxy=area/length,
        bending_stiffness_proxy=ip/length**3,out_of_plane_stiffness_proxy=op/length**3,
        rest_length=length,reference_length=8/np.sqrt(3),baseline_width=1.,baseline_height=1.,
        anchor_nodes=graph['anchors'],parent=np.array(parent),parent_paths=paths,core_node_count=len(graph['nodes']))

def profiles(part,net):
    outer=Polygon(part.rim_polygon.exterior);groups={}
    for (a,b),w,h in zip(net['edges'],net['width'],net['height']):
        groups.setdefault(round(float(h),1),[]).append(LineString(net['nodes'][[a,b]]).buffer(float(w)/2,quad_segs=4))
    return {h:set_precision(unary_union(shapes).intersection(outer),.0001).simplify(.0002,preserve_topology=True) for h,shapes in groups.items()}

def projected_volume(part,layers):
    cumulative=Polygon();volume=0.;last=0
    levels=sorted(layers)
    for low,high in zip([0]+levels[:-1],levels):
        shape=unary_union([p for h,p in layers.items() if h>=high]);volume+=(high-low)*shape.difference(part.rim_polygon).area
    return float(volume)

def build_geometry(part,graph,source,config,target_volume=None):
    def trial(s):
        f=field_values(graph,source,config,s);net=network(graph,f);layers=profiles(part,net)
        return f,net,layers,projected_volume(part,layers)
    values=trial(1.)
    if target_volume is not None and config['adaptation']!='uniform' and config.get('response')!='comply':
        lo=0.;hi=1.;best=trial(0.)
        for _ in range(14):
            mid=(lo+hi)/2;v=trial(mid)
            if v[3]<=target_volume:lo=mid;best=v
            else:hi=mid
        values=best
    return values

def export(part,layers,path):
    slabs=[]
    for h,shape in layers.items():
        for p in (shape.geoms if hasattr(shape,'geoms') else [shape]):
            if p.area>1e-7:slabs.append(trimesh.creation.extrude_polygon(p,float(h),engine='earcut'))
    mesh=trimesh.boolean.union([part.rim,*slabs],engine='manifold')
    # Collapse sub-micron Boolean slivers before STL float32 serialization.
    solid=manifold3d.Manifold(manifold3d.Mesh(np.asarray(mesh.vertices,dtype=np.float32),np.asarray(mesh.faces,dtype=np.uint32))).simplify(.001)
    simplified=solid.to_mesh();mesh=trimesh.Trimesh(simplified.vert_properties[:,:3],simplified.tri_verts,process=True)
    out=mesh.copy();out.apply_translation([*part.center[:2],0]);path.parent.mkdir(parents=True,exist_ok=True);out.export(path)
    reread=trimesh.load_mesh(path,process=True);check=dict(watertight=bool(reread.is_watertight),single_body=bool(reread.body_count==1),finite=bool(np.isfinite(reread.vertices).all()),duplicate_faces=int(len(reread.faces)-reread.unique_faces().sum()),degenerate_faces=int((~reread.nondegenerate_faces()).sum()),bounds=reread.bounds.tolist(),volume_mm3=float(reread.volume),sha256=sha256(path),layer_quantum_mm=.1,levels_mm=sorted(layers))
    check['bounds_preserved']=bool(np.allclose(reread.extents,part.mesh.extents,atol=.02))
    check['valid']=all(check[k] for k in ['watertight','single_body','finite','bounds_preserved']) and check['duplicate_faces']==0 and check['degenerate_faces']==0
    if not check['valid']:raise ValueError(f'Invalid exported mesh: {check}')
    missing=trimesh.boolean.difference([part.rim,mesh],engine='manifold');check['missing_rim_mm3']=float(abs(missing.volume))
    if check['missing_rim_mm3']>.01:raise ValueError('Rim removed')
    return mesh,check

def cells(graph,result,fields):
    output=[];prefix={'honeycomb':'H','triangle':'T','diamond':'D'}[graph['kind']]
    for i,(poly,ids) in enumerate(zip(graph['polygons'],graph['cell_nodes'])):
        ids=np.unique(ids);c=affine_fit(graph['nodes'][ids],result['formed_nodes'][ids]);center=np.array(poly.centroid.coords[0]);near=np.where(np.isin(graph['edges'],ids).all(axis=1))[0]
        if not len(near):near=np.argsort(np.linalg.norm(graph['nodes'][graph['edges']].mean(axis=1)-center,axis=1))[:len(ids)]
        c.update(id=i,cell_id=f'{prefix}{i+1:03d}',center=center.tolist(),polygon=np.array(poly.exterior.coords).tolist(),
            demand=float(result['parent_demand'][near].max()),width=float(fields['width'][near].mean()),height=float(fields['height'][near].mean()),area=float((fields['width'][near]*fields['height'][near]).mean()),
            boundary=bool(set(ids).intersection(graph['anchors'])),xy_feed=float(np.linalg.norm(result['formed_nodes'][ids,:2]-graph['nodes'][ids],axis=1).mean()))
        c.update(mechanism(c));output.append(c)
    return output
