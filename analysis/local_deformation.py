"""Geometric affine fit from reference XY to a fitted local tangent plane.

X @ F.T approximates (Y - mean(Y)) @ tangent.T. Singular values are
principal stretches; right singular vectors are directions in reference XY.
This cell-scale fit is not a constitutive polymer tensor.
"""
import numpy as np

MECHANISM_RULES = dict(low_stretch=1.10, directional_ratio=1.15,
    area_stretch=1.20, min_biaxial=1.04, axial_demand_pct=30.,
    feed_mm=2., boundary_sensitivity_pp=1., low_feed_mm=2.)

def affine_fit(flat, formed):
    x=np.asarray(flat,float);y=np.asarray(formed,float)
    x=x-x.mean(axis=0);y=y-y.mean(axis=0)
    if len(x)<3 or np.linalg.matrix_rank(x)<2:raise ValueError('Degenerate reference neighborhood')
    _,surface_s,vt=np.linalg.svd(y,full_matrices=False)
    if surface_s[1]<1e-10:raise ValueError('Collapsed formed neighborhood')
    normal=vt[-1].copy()
    if normal[2]<0:normal*=-1
    seed=np.array([1.,0,0]) if abs(normal[0])<.9 else np.array([0.,1,0])
    t1=seed-normal*np.dot(seed,normal);t1/=np.linalg.norm(t1)
    tangent=np.array([t1,np.cross(normal,t1)])
    target=y@tangent.T
    coef,_,rank,_=np.linalg.lstsq(x,target,rcond=None);f=coef.T
    u,s,vh=np.linalg.svd(f)
    directions=vh.copy()
    for i in range(2):
        if directions[i,np.argmax(abs(directions[i]))]<0:directions[i]*=-1;u[:,i]*=-1
    residual=np.sqrt(np.mean(np.sum((x@f.T-target)**2,axis=1)))
    relative_residual=float(residual/max(np.sqrt(np.mean(np.sum(target**2,axis=1))),1e-12))
    return dict(F=f.tolist(),lambda1=float(s[0]),lambda2=float(s[1]),J=float(np.prod(s)),
        anisotropy=float(s[0]/max(s[1],1e-12)),principal_direction_1=directions[0].tolist(),
        principal_direction_2=directions[1].tolist(),formed_direction_1=(tangent.T@u[:,0]).tolist(),
        formed_direction_2=(tangent.T@u[:,1]).tolist(),tangent_basis=tangent.tolist(),
        normal=normal.tolist(),fit_rms_mm=float(residual),out_of_plane_rms_mm=float(np.sqrt(np.mean((y@normal)**2))),
        signed_jacobian=float(np.linalg.det(f)),fit_relative_rms=relative_residual,
        fit_warning=bool(relative_residual>.20 or np.linalg.det(f)<=0),
        reference_condition=float(np.linalg.cond(x)),direction_resolved=bool(s[0]/max(s[1],1e-12)>1.02))

def mechanism(c,rules=None):
    r={**MECHANISM_RULES,**(rules or {})};flags=[];reasons=[]
    if c['anisotropy']>=r['directional_ratio']:
        flags.append('DIRECTIONAL COMPLIANCE');reasons.append(f"λ1/λ2 = {c['anisotropy']:.2f} ≥ {r['directional_ratio']}")
    if c['lambda2']>r['min_biaxial'] and c['J']>r['area_stretch']:
        flags.append('AREA EXPANSION');reasons.append(f"λ2 = {c['lambda2']:.2f}; J = {c['J']:.2f}")
    sensitivity=c.get('boundary_sensitivity_pp')
    if c['boundary'] and c['xy_feed']>r['feed_mm'] and sensitivity is not None and abs(sensitivity)>r['boundary_sensitivity_pp']:
        flags.append('BOUNDARY FEED');reasons.append(f"XY = {c['xy_feed']:.2f} mm; Δ demanda ao reduzir restrição = {sensitivity:+.2f} p.p.")
    if c['demand']>r['axial_demand_pct'] and c['xy_feed']<r['low_feed_mm']:
        flags.append('MATERIAL RESERVE');reasons.append(f"Demanda axial {c['demand']:.1f}% e XY feed < {r['low_feed_mm']} mm")
    category='MIXED' if len(flags)>1 else flags[0] if flags else 'LOW DEMAND' if c['lambda1']<r['low_stretch'] and c['demand']<10 else 'MIXED'
    if not reasons:reasons=['Baixa demanda segundo os limiares.' if category=='LOW DEMAND' else 'Sem mecanismo isolado pelos limiares; investigação necessária.']
    return dict(mechanism=category,mechanism_flags=flags,mechanism_reason='; '.join(reasons),boundary_sensitivity_available=sensitivity is not None)

def analyze_cells(part,base,result,sensitivity=None):
    cells=[]
    for i,edge_ids in enumerate(base['cell_edges']):
        ids=np.unique(base['edges'][edge_ids]);flat=np.asarray(result['nodes'])[ids];formed=np.asarray(result['formed_nodes'])[ids]
        c=affine_fit(flat,formed)
        c.update(id=i,cell_id=('H' if part.id=='hab2' else 'S')+f'{i+1:03d}',center=flat.mean(axis=0).tolist(),
            formed_center=formed.mean(axis=0).tolist(),node_ids=ids.tolist(),boundary=bool(base['boundary'][ids].any()),
            xy_feed=float(np.linalg.norm(formed[:,:2]-flat,axis=1).mean()),demand=float(np.asarray(result['parent_demand'])[edge_ids].max()))
        if sensitivity is not None:c['boundary_sensitivity_pp']=float(np.asarray(sensitivity['parent_demand'])[edge_ids].max()-c['demand'])
        c.update(mechanism(c));cells.append(c)
    return cells
