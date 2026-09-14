import json
import shutil
import zipfile
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from analysis.geometry import ROOT

def plot_pair(original,candidate,part,path,field='demand'):
    fig,axs=plt.subplots(1,2,figsize=(8,6),layout='constrained')
    for ax,item in zip(axs,[original,candidate]):
        data=json.loads((ROOT/'dist'/item[part]['data']).read_text(encoding='utf-8'))
        lines=[np.array(e['flat']).reshape(2,3)[:,:2] for e in data['edges']]
        values=[e['delta'] if field=='delta' else max(0,e['demand']) for e in data['edges']]
        lc=LineCollection(lines,array=np.array(values),cmap='RdBu_r' if field=='delta' else 'RdYlGn_r',linewidths=2)
        lc.set_clim((-30,30) if field=='delta' else (0,40));ax.add_collection(lc)
        ax.set(xlim=(-42,42),ylim=(-54,54),aspect='equal');ax.axis('off');ax.set_title(item['name'])
    fig.colorbar(lc,ax=axs,label='Delta (percentage points)' if field=='delta' else 'Relative demand (%) — saturated at 40')
    fig.suptitle(f'{part}: relative model, not calibrated material failure')
    fig.savefig(path,dpi=140);plt.close(fig)

def finish_outputs(catalog):
    folder=ROOT/'docs/figures';folder.mkdir(parents=True,exist_ok=True)
    items=catalog['designs'];original=items[0]
    winner=next((d for d in items if d['id']==catalog['recommendation']['candidate_id']),None)
    focus=winner or min(items[1:],key=lambda d:d['combined_risk'])
    catalog['inspection_default_id']=focus['id']
    for part in ['hab2','submerged']:
        plot_pair(original,focus,part,folder/f'risk_map_{part}.png')
        plot_pair(original,focus,part,folder/f'delta_map_{part}.png','delta')
    fig,ax=plt.subplots(figsize=(8,5),layout='constrained')
    for family in ['original','reserve','boundary','hybrid']:
        group=[d for d in items if d['family']==family]
        x=[np.mean([d[p]['metrics']['material_change_pct'] for p in ['hab2','submerged']]) for d in group]
        y=[d['combined_risk'] for d in group]
        ax.scatter(x,y,label=family,s=50)
        for a,b,d in zip(x,y,group):ax.annotate(d['intensity'],(a,b),fontsize=7,xytext=(3,3),textcoords='offset points')
    ax.axhline(1,color='gray',ls='--');ax.set(xlabel='Mean projected material change (%)',ylabel='Mean Risk Index',title='Two-part comparison — material is excluded from risk');ax.legend()
    fig.savefig(folder/'comparison.png',dpi=160);plt.close(fig)
    report=['# LampForm Lab v0.5 — Engineering report','',f'Generated: {catalog["generated_at"]}', '',
      '## Baseline problem','',
      'The supplied v0.1 and v0.2 solvers were reproduced without editing legacy; deviations below 0.02 percentage point are recorded in `generated/baseline_reproduction.json`. '
      'This DOE recomputes its own baseline with exactly the candidate solver. It merges nominally coincident corners at 0.03 mm and includes 20 actual rim connectors: 246 parent ligaments per part. '
      'Reported demand is the maximum positive segment strain per physical parent, so subdividing a connector does not dilute percentiles. '
      'The original STL are copied byte-for-byte; both contain 503 duplicated faces and are not watertight.', '',
      '## Design space and mechanisms','',
      'Ten initial designs: Original and Low/Medium/High Reserve, Boundary and Hybrid. Reserve reduces cell openings by up to 2/6/10%, spatially smoothed over 12 mm. '
      'Boundary contracts the core to 99/98/96% and adds actual S connectors, width 1.20/1.05/0.95 mm and maximum amplitude 0.15/0.35/0.65 mm. '
      'Hybrid combines these levels. Nominal boundary-band parameters 0.4/0.8/1.6 mm are converted to isotropic scale using a 40 mm reference; actual gap varies along the perimeter. '
      'Boundary changes pitch and connectors together: their individual effects are not isolated. '
      'If no pair passes, a bounded second pass tests reserve strengths 0.005, 0.01, 0.035, stopping at the first pass or 13 designs total. '
      'Every attempted result is stored in `generated/sweep/` and exposed in the explorer.', '',
      '## Danger zones and risk','',
      'LOW <10%; MODERATE 10–<20%; HIGH 20–30%; CRITICAL >30%. These are relative demand classes, not polymer failure limits. '
      'Risk Index = 0.30(P95/P95₀) + 0.25(P99/P99₀) + 0.25(max/max₀) + 0.20(critical fraction/critical fraction₀). '
      'Material and open area are excluded. If baseline has zero critical ligaments the denominator floor is one edge. '
      'Print gate requires lower P95, fewer >30% ligaments, max ≤ baseline +5 percentage points, valid geometry, closed single body, minimum structural path width and aperture probe. '
      'A pair is recommended only when BOTH parts pass. Gates are selection heuristics, not a safety certification.', '',
      '## Results','', '| Design | Part | P95 | P99 | Max | Critical | Risk | Material Δ | Gate |', '|---|---|---:|---:|---:|---:|---:|---:|---|']
    for d in items:
        for p in ['hab2','submerged']:
            m=d[p]['metrics'];g=d[p]['gate']
            report.append(f'| {d["name"]} | {p} | {m["p95"]:.2f}% | {m["p99"]:.2f}% | {m["maximum"]:.2f}% | {m["critical_edges"]} | {m["risk_index"]:.3f} | {m["material_change_pct"]:+.1f}% | {g["status"]} |')
    report += ['', '![Risk versus material](figures/comparison.png)', '', '## Sensitivity: material, boundary or combination?', '']
    for family in ['reserve','boundary','hybrid']:
        group=[d for d in items if d['family']==family and not d['intensity'].startswith('search')]
        risks=[d['combined_risk'] for d in group]
        report.append(f'- {family.title()}: two-part Risk Index range {min(risks):.3f}–{max(risks):.3f}; {sum(d["gate"]["passed"] for d in group)} pairs passed.')
    ranking=sorted(['reserve','boundary','hybrid'],key=lambda f:min(d['combined_risk'] for d in items if d['family']==f))
    report += ['',f'The smallest observed risk in this tested space belongs to {ranking[0]}. This is a comparison of tested perturbations, not a causal attribution or proof of global optimality. '
      'The boundary family alters both pitch and connector shape. A matched-pitch follow-up and physical measurements are needed to isolate rim feed from material amount.', '',
      '## Rejected candidates','']
    for d in items[1:]:
        if not d['gate']['passed']:report.append(f'- {d["name"]}: '+', '.join(d['gate']['reasons']))
    report += ['', '## Geometry changes and map correspondence','',
      'Parent IDs preserve lattice topology and the same attachment sites across designs; cell IDs preserve original centers, with scaled positions in boundary families. '
      'Delta = candidate parent demand − original parent demand, in percentage points. The maps show exact flat footprints plus the corresponding analytical paths. '
      'Equivalent hole size = sqrt(2×hole area/sqrt(3)); this is across-flats only for a regular hexagon. Curved candidates use area-equivalent size. '
      'Geometry changed % is symmetric-difference area divided by union area, excluding the retained rim. Hole outlines are re-extracted after all unions/cuts. '
      'The formed view shows the analytical network, never a fabricated deformed solid. Its five steps are actual continuation solutions.', '',
      '![HAB-2 risk](figures/risk_map_hab2.png)', '![HAB-2 delta](figures/delta_map_hab2.png)',
      '![Sub-Merged risk](figures/risk_map_submerged.png)', '![Sub-Merged delta](figures/delta_map_submerged.png)', '',
      '## Solver limitations','',
      'Geometric draping on the STL top envelope, relative axial stiffness, angular penalty, curved material paths and XY feed are modeled. '
      'Axial energy scales with width and segment length; angular energy with width cubed and inverse adjacent length. '
      'Every design uses the same rim anchor 2.0, interior anchor 0.0005 and angular weight 0.01. Compliance is actual path length/shape, not an arbitrary anchor discount. '
      'Solutions are local minima; convergence by tolerance does not prove global optimality. Cost, optimality and continuation stages are retained. '
      'Not modeled: calibrated polymer stress, temperature, E(T), viscoelasticity, heating rate, contact friction, layer anisotropy, damage or real failure strain. '
      'The solid rim is not a deformable volume mesh; contact is a top-envelope approximation.', '',
      '## STL validation and manufacturing','',
      'Defaults in `config/manufacturing.yaml`: 0.4 mm line, 0.8 mm structural path, 0.4 mm main-cell gap probe, 1 mm lattice and 4 mm retained rim. '
      'Candidates are planar extrusions united with the exact original rim via Manifold and reread from the binary STL. '
      'Checks: watertight, one body, no degenerate or duplicate faces, consistent winding, finite coordinates, global dimensions within 0.02 mm and no missing rim volume over 0.01 mm³. '
      'The 0.8 mm check covers swept structural paths; the gap probe must fit each main cell. It does not certify every tapered corner, peripheral slot or printer profile. '
      'The volume proxy uses original rim volume plus planar area outside the rim times thickness, consistently even for the defective original. '
      'All manufacturing flags remain separate from structural gates.', '',
      '## Physical test recommendation','',catalog['recommendation']['status'], '',catalog['recommendation']['reason'],'']
    if winner:
        out=ROOT/'dist/downloads/print-test-v1';out.mkdir(parents=True,exist_ok=True)
        for p,label in [('hab2','HAB-2'),('submerged','SubMerged')]:
            src=ROOT/'dist'/winner[p]['stl']
            shutil.copyfile(src,out/f'{label}_TEST_V1.stl')
            named=f'downloads/{label}_TEST_V1_{winner["id"]}.stl';shutil.copyfile(src,ROOT/'dist'/named)
            catalog['recommendation'][p+'_stl']=named
        for image in ['comparison.png','risk_map_hab2.png','risk_map_submerged.png']:shutil.copyfile(folder/image,out/image)
        (out/'parameters.json').write_text(json.dumps(winner['parameters'],indent=2))
        (out/'metrics.json').write_text(json.dumps({p:winner[p] for p in ['hab2','submerged']},ensure_ascii=False,indent=2),encoding='utf-8')
        (out/'README.txt').write_text('PRINT TEST V1\nDesign: '+winner['name']+'\nWhy selected: '+catalog['recommendation']['reason']+'\n'
            +'\n'.join(winner[p]['why'] for p in ['hab2','submerged'])+'\nFlat pieces, mm; lattice 1, rim 4. Review slicer layers. '
            'Print Original and candidate with the same material, orientation and thermal procedure; photograph and measure openings, feed and rupture. '
            'Relative model, no calibrated material failure limits. Original source STL have defects retained unchanged.',encoding='utf-8')
        archive=ROOT/'dist/downloads/LAMPFORM_PRINT_TEST_V1.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for file in out.iterdir():z.write(file,file.name)
        catalog['recommendation']['zip']='downloads/LAMPFORM_PRINT_TEST_V1.zip'
        report += ['RECOMMENDED PHYSICAL TEST',f'Original vs {winner["name"]}', '',
            f'- Candidate: `HAB-2_TEST_V1_{winner["id"]}.stl` and `SubMerged_TEST_V1_{winner["id"]}.stl`.',
            '- Reference: `dist/downloads/original/HAB-2.stl` and `dist/downloads/original/Sub-Merged.stl`.']
    else:report += ['NO ROBUST IMPROVEMENT FOUND YET', '', 'No PRINT TEST V1 archive is labeled as approved. Candidate STL remain available as explicitly unapproved exploratory geometries.']
    (ROOT/'docs/LAMPFORM_V05_ENGINEERING_REPORT.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
