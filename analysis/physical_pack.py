import csv,json,shutil,zipfile,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analysis.geometry import ROOT
from analysis.run_design_sweep import write_json
from analysis.solver import DEFAULTS

FIELDS='experiment_id sample_id date part design material filament_brand filament_batch nozzle_mm line_width_mm layer_height_mm print_temperature_c bed_temperature_c print_orientation heating_device heating_power heating_distance_mm heating_time_s surface_temperature_c forming_time_s hold_time_s cooling_time_s cell_id L1_before_mm L1_after_mm L2_before_mm L2_after_mm failure failure_type notes'.split()
PROCEDURE='''# EXPERIMENT V1 — MECHANISM SCREENING

Primeiro experimento: Sub-Merged, A/B/C/D. A é o original reparado, B acrescenta reserva apenas no interior, C modifica apenas dois conectores longos fora do núcleo e D combina exatamente B e C. Não há promessa de melhora física.

1. Imprimir A/B/C/D com o mesmo material, lote, orientação e perfil. Inspecionar todas as camadas no fatiador. Registrar as condições reais; não usar valores térmicos inventados.
2. Marcar as células selecionadas no mapa e identificar amostra e experimento. Fazer réplicas independentes quando possível; não confundir células com réplicas.
3. Fotografar a peça plana com escala e orientação de referência.
4. Posicionar no molde real, preservando a orientação.
5. Aquecer sob uma condição previamente definida para o material/equipamento. Registrar potência, distância e tempo.
6. Medir e registrar a temperatura superficial e o método de medição.
7. Executar o fechamento e registrar tempo/deslocamento.
8. Manter pelo tempo definido, registrando-o.
9. Resfriar sob condição repetível; registrar tempo.
10. Retirar a peça.
11. Fotografar com escala e referência de orientação.
12. Medir as células selecionadas. Definir dois segmentos materiais antes do teste, alinhados às direções de referência d1/d2 do mapa. Seguir os MESMOS pontos após formar; não reordenar L1/L2 pelo tamanho observado. Medidas são comprimentos de corda local, não percurso de um ligamento curvo. A curvatura e o ajuste afim geram erro de aproximação. Registrar fotos e método.
13. Registrar OK, stretched, opened, cracked, ruptured, wrinkled ou other; definir failure=true/false explicitamente e manter o mesmo critério entre amostras.
14. Importar CSV/JSON no LampForm. Comparar primeiro o ranking espacial. Não preencher células não medidas com zero.

## Calibration ≠ validation

Reservar amostras Original para calibração. Congelar parâmetros antes de abrir medidas Candidate de validação. Reportar por amostra; não combinar processos térmicos diferentes. Nenhum resultado físico foi registrado nesta versão.
'''

def measurement_plan(cells):
    groups=[[c for c in cells if lo<=c['demand']<hi] for lo,hi in [(0,10),(10,20),(20,30),(30,float('inf'))]]
    groups += [[c for c in cells if c['boundary']],[c for c in cells if not c['boundary']]]
    groups=[sorted(g,key=lambda c:c['cell_id']) for g in groups]
    chosen=[]
    while len(chosen)<20:
        moved=False
        for g in groups:
            candidate=next((c for c in g if c['cell_id'] not in chosen),None)
            if candidate and len(chosen)<20:chosen.append(candidate['cell_id']);moved=True
        if not moved:break
    return chosen

def reference_map(data,cells,selected,path):
    svg=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="-42 -54 84 110"><rect x="-42" y="-54" width="84" height="110" fill="#f4f5ef"/>']
    fig,ax=plt.subplots(figsize=(8,10));fig.patch.set_facecolor('#f4f5ef');ax.set_facecolor('#f4f5ef')
    for geom,c in zip(data['cells'],cells):
        p=np.array(geom['candidate']);color='#b5d2b4' if c['cell_id'] in selected else '#ffffff'
        ax.fill(p[:,0],p[:,1],color=color,edgecolor='#607767',lw=.5)
        x,y=c['center'];ax.text(x,y,c['cell_id'],ha='center',va='center',fontsize=6)
        dx,dy=np.array(c['principal_direction_1'])*2
        ax.plot([x-dx,x+dx],[y-dy,y+dy],color='#316a90',lw=.6)
        points=' '.join(f'{a:.4f},{-b:.4f}' for a,b in p)
        svg.append(f'<polygon points="{points}" fill="{color}" stroke="#607767" stroke-width=".12"/><path d="M{x-dx},{-y+dy} L{x+dx},{-y-dy}" stroke="#316a90" stroke-width=".15"/><text x="{x}" y="{-y}" text-anchor="middle" font-size="1.8" font-family="sans-serif">{c["cell_id"]}</text>')
    svg.append('</svg>');path.write_text(''.join(svg),encoding='utf-8')
    ax.set(xlim=(-42,42),ylim=(-54,54),aspect='equal');ax.axis('off');fig.tight_layout();fig.savefig(path.with_suffix('.png'),dpi=160);plt.close(fig)

def build_pack(catalog):
    out=ROOT/'dist/downloads/physical-test-v1';out.mkdir(parents=True,exist_ok=True)
    plans={};predictions={}
    for p,label in [('hab2','HAB2'),('submerged','SUBMERGED')]:
        original=catalog['designs'][0][p];repaired=next(d for d in catalog['designs'] if d['id']=='test_a')[p]
        shutil.copyfile(ROOT/'dist'/original['stl'],out/f'ORIGINAL_{label}.stl')
        shutil.copyfile(ROOT/'dist'/repaired['stl'],out/f'{label}_original_repaired_for_test.stl')
        data=json.loads((ROOT/'dist'/original['data']).read_text(encoding='utf-8'));cells=json.loads((ROOT/'dist'/original['local_data']).read_text(encoding='utf-8'))
        plans[p]=measurement_plan(cells)
        reference_map(data,cells,[],out/f'cell_reference_map_{p}.svg')
        reference_map(data,cells,plans[p],out/f'measurement_plan_{p}.svg')
    for key,name in [('test_a','TEST_A_ORIGINAL'),('test_b','TEST_B_RESERVE'),('test_c','TEST_C_BOUNDARY'),('test_d','TEST_D_HYBRID')]:
        d=next(d for d in catalog['designs'] if d['id']==key);shutil.copyfile(ROOT/'dist'/d['submerged']['stl'],out/f'{name}.stl')
    for d in catalog['designs']:
        predictions[d['id']]={p:json.loads((ROOT/'dist'/d[p]['local_data']).read_text(encoding='utf-8')) for p in ['hab2','submerged'] if p in d}
    for filename in ['cell_reference_map','measurement_plan']:
        for ext in ['svg','png']:shutil.copyfile(out/f'{filename}_submerged.{ext}',out/f'{filename}.{ext}')
    with (out/'experiment_template.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader()
        for design in catalog['causal_tests']:
            for cell in plans['submerged']:writer.writerow(dict(part='submerged',design=design,cell_id=cell))
    (out/'sensor_template.csv').write_text('time_s,displacement_mm,force_n,temperature_c\n')
    (out/'test_procedure.md').write_text(PROCEDURE,encoding='utf-8')
    (out/'README.md').write_text('# LAMPFORM PHYSICAL TEST V1\n\nSub-Merged A/B/C/D: experimento para aprender mecanismos. HAB-2: original reparado vs Reserve escolhido independentemente.\n\nORIGINAL_* são os arquivos fornecidos, com defeitos preservados. TEST_A e *_repaired_for_test reconstroem a extrusão de 1 mm da pegada nominal e fazem união Manifold com o aro original de 4 mm. Não há alteração intencional do padrão; tolerância de exportação 0,0001 mm. C preserva núcleo e furos; modifica somente dois conectores longos. Os conectores curtos permanecem iguais.\n\nMapas sem sufixo referem-se ao Sub-Merged. Azul indica direção d1 de referência; use d2 perpendicular. IDs estáveis H001–H065 e S001–S065. Campo de deformação de seis nós por célula; direção pouco determinada quando λ1/λ2 ≤1,02. CSV contém células planejadas, SEM medições inventadas.\n\nNO PHYSICAL VALIDATION DATA YET. Inspecione camadas antes de imprimir. Consulte test_procedure.md.\n',encoding='utf-8')
    write_json(out/'predictions.json',predictions)
    write_json(out/'parameters.json',dict(version='0.6.0',solver_defaults=DEFAULTS,
        source_hashes={name:hashlib.sha256((ROOT/'analysis'/name).read_bytes()).hexdigest() for name in ['solver.py','local_deformation.py','physical_candidates.py']},
        causal_tests={d['id']:dict(parameters=d.get('parameters'),geometry=d['submerged'].get('causal'),stl_sha256=d['submerged']['validation']['sha256']) for d in catalog['designs'] if d['id'] in catalog['causal_tests']},
        manufacturing=catalog['manufacturing'],mechanism_rules=catalog['mechanism_rules']))
    write_json(ROOT/'dist/data/physical/measurement_plan.json',plans)
    with zipfile.ZipFile(ROOT/'dist/downloads/LAMPFORM_PHYSICAL_TEST_V1.zip','w',zipfile.ZIP_DEFLATED) as z:
        for file in out.iterdir():z.write(file,file.name)
    return plans
