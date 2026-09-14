import json,zipfile,shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from analysis.geometry import ROOT
from analysis.run_design_sweep import write_json

def picture(data,path,field,title):
    fig,ax=plt.subplots(figsize=(8,9));fig.patch.set_facecolor('#f4f5ef');ax.set_facecolor('#f4f5ef')
    segments=np.array([e['flat'] for e in data['edges']]).reshape(-1,2,3)[:,:,:2]
    values=np.array([e[field] for e in data['edges']]);lines=LineCollection(segments,cmap='viridis',linewidths=2);lines.set_array(values)
    lines.set_clim((.8,2) if field=='height' else (.8,1.6) if field=='width' else (0,50));ax.add_collection(lines);ax.set(xlim=(-42,42),ylim=(-54,54),aspect='equal');ax.axis('off');ax.set_title(title)
    fig.colorbar(lines,ax=ax,shrink=.6,label='mm' if field in ['width','height'] else 'demand %');fig.tight_layout();fig.savefig(path,dpi=180);plt.close(fig)

def build_packs(catalog):
    summary=[]
    for part in ['hab2','submerged']:
        out=ROOT/f'dist/downloads/parametric/{part}/test-v2';out.mkdir(parents=True,exist_ok=True)
        selected=[next(e for e in catalog['designs'] if e['id']==id and e['part']==part) for id in catalog['doe']]
        predictions={}
        fig,axes=plt.subplots(1,4,figsize=(19.2,10.8),facecolor='#f4f5ef')
        for e,ax in zip(selected,axes):
            data=json.loads((ROOT/'dist'/e['data']).read_text());predictions[e['id']]=dict(metrics=e['metrics'],cells=data['cells'],solver=data['solver'])
            shutil.copyfile(ROOT/'dist'/e['stl'],out/f'{e["id"]}.stl')
            pts=np.array([r['flat'] for r in data['edges']]).reshape(-1,2,3)[:,:,:2];lines=LineCollection(pts,cmap='viridis',linewidths=2);lines.set_array(np.array([r['height'] for r in data['edges']]));lines.set_clim(.8,2);ax.add_collection(lines);ax.set(xlim=(-42,42),ylim=(-54,54),aspect='equal');ax.axis('off');ax.set_title(e['name'],fontsize=12);ax.set_facecolor('#f4f5ef')
            ax.text(.5,-.02,f'P95 {e["metrics"]["p95"]:.1f}%\nMaterial {e["metrics"]["material_delta_pct"]:+.1f}%',transform=ax.transAxes,ha='center')
            picture(data,out/f'{e["id"]}_width_map.png','width',e['name']+' · width / mm')
            picture(data,out/f'{e["id"]}_height_map.png','height',e['name']+' · height / mm')
        fig.suptitle(f'{part.upper()} · Width / height DOE\nCalculated geometry, not physical validation',fontsize=21);fig.savefig(out/'comparison.png',dpi=100);plt.close(fig)
        shutil.copyfile(out/'D_both_width_map.png',out/'width_map.png');shutil.copyfile(out/'D_both_height_map.png',out/'height_map.png')
        write_json(out/'parameters.json',{e['id']:dict(parameters=e['parameters'],validation=e['validation']) for e in selected});write_json(out/'predictions.json',predictions)
        (out/'README.md').write_text(f'''# Parametric test V2 — {part}

A_uniform: width 1 mm, total lattice height 1 mm. This is the generated reference for this DOE, not a silent replacement of the supplied original STL.
B_width: width adaptive, height uniform. C_height: width uniform, height adaptive. D_both: both adaptive.
The same honeycomb graph, rim and anchor definition is retained. Height levels use 0.1 mm increments. Junction ends use the maximum neighboring height; steps are limited to 0.2 mm between adjacent parent ligaments.

The +10% budget is a cap relative to A lattice volume, excluding the unchanged rim. Quantization can leave unused budget; parameters and actual mesh volumes are included. B and C should be compared using their measured volume difference, not their names alone.

Print with 0.1 mm printer layer height and the same material, orientation and process. Inspect slicer layers before printing. Record material batch, heating distance/time, surface temperature and forming/holding/cooling times. No printer job is sent by LampForm.

Variable height changes both structural stiffness and thermal response. The current model evaluates the structural/geometric effect. Local heating differences are not yet calibrated. Out-of-plane section inertia is stored but full out-of-plane bending is not solved.

NO PHYSICAL VALIDATION DATA YET. These are experiments, not final recommended designs. The original files and v0.6 test pack remain available separately.
''',encoding='utf-8')
        with zipfile.ZipFile(out.parent/'LAMPFORM_PARAMETRIC_TEST_V2.zip','w',zipfile.ZIP_DEFLATED) as z:
            for f in out.iterdir():z.write(f,f.name)
        summary.extend(selected)
    with zipfile.ZipFile(ROOT/'dist/downloads/LAMPFORM_PARAMETRIC_TEST_V2.zip','w',zipfile.ZIP_DEFLATED) as z:
        for part in ['hab2','submerged']:
            for f in (ROOT/f'dist/downloads/parametric/{part}/test-v2').iterdir():z.write(f,part+'/'+f.name)
    rows=['# v0.8 calculated catalogue','', 'Relative geometric model; no physical validation.','', '| Part | Design | P95 % | Max % | Critical >30% | Lattice volume mm³ | Material Δ % | Height mm | Converged |','|---|---|---:|---:|---:|---:|---:|---|---|']
    for e in catalog['designs']:
        m=e['metrics'];rows.append(f'| {e["part"]} | {e["name"]} | {m["p95"]:.2f} | {m["maximum"]:.2f} | {m["critical_edges"]} | {m["lattice_volume_mm3"]:.2f} | {m["material_delta_pct"]:+.2f} | {m["minimum_height_mm"]:.1f}–{m["maximum_height_mm"]:.1f} | {e["solver_converged"]} |')
    (ROOT/'docs/V08_CALCULATED_CATALOG.md').write_text('\n'.join(rows)+'\n',encoding='utf-8')
