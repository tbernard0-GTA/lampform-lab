"""Bounded, offline ranking calibration. Candidate measurements are held out."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import sys,json,itertools,hashlib
from pathlib import Path
if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from scipy.stats import spearmanr,rankdata
from analysis.geometry import ROOT,PAIRS,load_part,load_tool,sha256
from analysis.lattice import base_network
from analysis.local_deformation import analyze_cells
from analysis.solver import solve_design,DEFAULTS
from analysis.run_design_sweep import write_json

def group(rows):
    keys={(r['experiment_id'],r['sample_id'],r['part'],r['design']) for r in rows}
    if len(keys)!=1:raise ValueError('Each role requires one experiment/sample/part/design group')
    return next(iter(keys))

def validate_job(job):
    a=job['calibration'];b=job['validation'];ga=group(a);gb=group(b)
    if ga[3] not in ['original','test_a'] or gb[3] in ['original','test_a'] or ga[1]==gb[1] or ga[2]!=gb[2]:raise ValueError('Original calibration and distinct Candidate validation samples required')
    for rows in [a,b]:
        measured=[r for r in rows if r.get('L1_before_mm','')!='']
        if len(measured)<5:raise ValueError('At least five measured cells per role required')
        if len(set(r['cell_id'] for r in rows))!=len(rows):raise ValueError('Duplicate cells')
        for r in measured:
            if any(not np.isfinite(float(r[k])) or float(r[k])<=0 for k in ['L1_before_mm','L1_after_mm','L2_before_mm','L2_after_mm']):raise ValueError('Measurements must be positive and finite')
        if len(set(float(r['L1_after_mm'])/float(r['L1_before_mm']) for r in measured))<2:raise ValueError('Ranking unavailable for constant measurements')
    return ga,gb

def context(rows):
    _,_,p,design=group(rows);spec=next(s for s in PAIRS if s[0]==p);part=load_part(spec);base=base_network(part.centers)
    path=ROOT/f'generated/physical/{design}/{p}/lattice.json'
    if not path.exists():path=ROOT/f'generated/sweep/{design}/{p}_lattice.json'
    net=json.loads(path.read_text(encoding='utf-8'))
    for k in ['nodes','edges','width','rest_length','anchor_nodes','parent']:net[k]=np.array(net[k])
    return part,base,load_tool(spec),net

def evaluate(rows,ctx,parameters):
    part,base,tool,net=ctx;r=solve_design(part,tool,net,parameters);cells=analyze_cells(part,base,r);byid={c['cell_id']:c for c in cells};pairs=[]
    for row in rows:
        if row['cell_id'] not in byid:raise ValueError('Unknown cell ID')
        if row.get('L1_before_mm','')=='':continue
        pairs.append(dict(cell_id=row['cell_id'],predicted=byid[row['cell_id']]['lambda1'],measured=float(row['L1_after_mm'])/float(row['L1_before_mm'])))
    x=np.array([p['predicted'] for p in pairs]);y=np.array([p['measured'] for p in pairs]);rho=float(spearmanr(x,y).statistic)
    if not np.isfinite(rho):rho=None
    fit=dict(n=len(pairs),spearman=rho,rank_rmse=float(np.sqrt(np.mean(((rankdata(x)-rankdata(y))/len(x))**2))),lambda1_rmse=float(np.sqrt(np.mean((x-y)**2))),solver_converged=r['solver']['success'],pairs=pairs)
    return fit,cells

def main(path):
    job=json.loads(Path(path).read_text(encoding='utf-8-sig'));ga,gb=validate_job(job)
    payload={k:job[k] for k in ['calibration','validation']};digest=hashlib.sha256(json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    if job.get('dataset_digest') and digest!=job['dataset_digest']:raise ValueError('Dataset changed since export')
    ctx=context(job['calibration']);trials=[]
    configs=[dict(boundary_anchor=a,bending_weight=b,interior_anchor=f) for a,b,f in itertools.product([1.,3.],[.005,.02],[.00025,.001])]
    configs.insert(0,{k:DEFAULTS[k] for k in ['boundary_anchor','bending_weight','interior_anchor']})
    for parameters in configs:
        fit,_=evaluate(job['calibration'],ctx,parameters);trials.append(dict(parameters=parameters,fit=fit));print('Calibration',len(trials),'of',len(configs),fit['rank_rmse'],flush=True)
    accepted=[t for t in trials if t['fit']['solver_converged'] and t['fit']['spearman'] is not None]
    if not accepted:raise ValueError('No calibration solution converged')
    winner=min(accepted,key=lambda t:t['fit']['rank_rmse'])
    # Held-out measurements are first evaluated only AFTER the winner is frozen.
    validation,predictions=evaluate(job['validation'],context(job['validation']),winner['parameters'])
    output=dict(schema='lampform-calibration-result-v1',calibrated_on=' / '.join(ga),validation_sample=' / '.join(gb),dataset_digest=digest,
        parameters=winner['parameters'],calibration_fit=winner['fit'],validation_performance=validation,
        predictions=predictions,trials=trials,solver_sha256=sha256(ROOT/'analysis/solver.py'),
        limitations='Ranking fit, not polymer calibration. Axial scale fixed; absolute stiffness is not identifiable from this geometric experiment. Thermal process not modeled.')
    write_json(Path(path).with_name('calibration_result.json'),output)

if __name__=='__main__':main(sys.argv[1])
