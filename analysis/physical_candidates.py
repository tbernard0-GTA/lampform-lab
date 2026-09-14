"""Matched-core 2x2 experiment and two bounded mechanism concepts."""
import numpy as np
from shapely.geometry import LineString,Polygon
from shapely.ops import unary_union
from shapely.affinity import scale
from shapely import set_precision
from .candidates import make_design
from .geometry import cross_width
from .lattice import assemble_network,wave_path

def physical_design(part,base,contacts,kind,baseline,local):
    d=make_design(part,base,contacts,'original',baseline)
    source=d['material'];material=source;paths=d['paths'];widths=d['widths'].copy()
    # Core contains the complete nominal holes and every lattice centerline.
    # C may only change the remaining transition corridors outside this mask.
    core=unary_union([*part.cells,*[LineString(p).buffer(w/2+.05) for p,w in zip(paths,widths)]])
    changed=[]
    if kind in ['test_b','test_d']:
        interior=[i for i,e in enumerate(base['cell_edges']) if not base['boundary'][np.unique(base['edges'][e])].any()]
        material=set_precision(material,.00001).union(set_precision(unary_union([part.cells[i].difference(scale(part.cells[i],.965,.965,origin='centroid')) for i in interior]),.00001))
        widths=np.array([cross_width(material.union(part.rim_polygon).buffer(.0001),*p) for p in paths])
    if kind in ['test_c','test_d']:
        for i,c in enumerate(d['contacts']):
            old=LineString(c['path']);a,b=c['path'];length=old.length
            if length<4:continue
            free=old.difference(core.union(part.rim_polygon))
            segments=list(free.geoms) if hasattr(free,'geoms') else [free]
            segment=max(segments,key=lambda s:s.length)
            if segment.length<1.2:continue
            ends=np.array(segment.coords)[[0,-1]]
            if np.linalg.norm(ends[0]-a)>np.linalg.norm(ends[1]-a):ends=ends[::-1]
            proposed=np.vstack([a,wave_path(*ends,.25,12),b]);wave=LineString(proposed).buffer(.5,quad_segs=8)
            corridor=old.buffer(c['width']/2+.3,cap_style=2)
            zone=corridor.union(wave).difference(core.union(part.rim_polygon))
            trial=material.difference(zone).union(wave.intersection(zone))
            if not trial.union(part.rim_polygon).buffer(.001).covers(LineString(proposed)):continue
            material=trial;c['path']=proposed;c['width']=1.;changed.append(i)
        if not changed:raise ValueError('No boundary-only intervention fits outside the fixed core')
    if kind in ['directional','area']:
        used=set()
        for i,(edge,path) in enumerate(zip(base['edges'],paths)):
            if base['boundary'][edge].any() or used.intersection(edge):continue
            center=path.mean(axis=0);cell=min(local,key=lambda c:np.linalg.norm(center-c['center']))
            direction=(path[-1]-path[0]);direction/=np.linalg.norm(direction)
            target=(cell['anisotropy']>1.12 and abs(np.dot(direction,cell['principal_direction_1']))>.75) if kind=='directional' else cell['J']>1.15
            if not target:continue
            new=wave_path(*path,.4,10);cut=LineString([path[0]+.55*direction,path[1]-.55*direction]).buffer(widths[i]/2+.2,cap_style=2)
            material=material.difference(cut).union(LineString(new).buffer(.5,quad_segs=8))
            paths[i]=new;widths[i]=1.;changed.append(i);used.update(edge)
        if not changed:raise ValueError('No mechanism-aligned path selected')
    material=material.buffer(0)
    solid=material.union(part.rim_polygon)
    voids=[Polygon(r) for p in (solid.geoms if hasattr(solid,'geoms') else [solid]) for r in p.interiors]
    holes=[]
    for p in part.cells:
        matches=[h for h in voids if h.covers(p.centroid)]
        if len(matches)!=1 or matches[0].buffer(-.2).is_empty:raise ValueError(f'Lost main cell opening: {p.centroid.wkt}, matches={len(matches)}')
        holes.append(matches[0])
    for path in paths+[c['path'] for c in d['contacts']]:
        if not solid.buffer(.025).covers(LineString(path)):raise ValueError('Path outside physical material')
    lattice=assemble_network(base,paths,widths,d['contacts'],part.thickness,d['lattice']['baseline_width'])
    core_delta=material.intersection(core).symmetric_difference(source.intersection(core)).area
    if kind=='test_c' and core_delta>1e-7:raise ValueError(f'Boundary-only changed core: {core_delta}')
    d.update(id=kind,material=material,holes=holes,paths=paths,widths=widths,lattice=lattice,
        candidate_cell_width=widths[base['cell_edges']].mean(axis=1),
        hole_size=np.array([np.sqrt(h.area*2/np.sqrt(3)) for h in holes]),
        parameters=dict(concept=kind,reserve_hole_scale=.965,boundary_amplitude_mm=.25,
            boundary_width_mm=1.,interior_amplitude_mm=.4,interior_width_mm=1.,
            core_scale=1.,pitch_mm=base['pitch'],changed_paths=changed),
        causal=dict(core_changed_area_mm2=float(core_delta),core_mask=core.wkt,
            original_pitch=base['pitch'],core_node_positions_unchanged=True,
            original_holes_preserved=all(a.symmetric_difference(b).area<1e-7 for a,b in zip(part.cells,holes))))
    return d

