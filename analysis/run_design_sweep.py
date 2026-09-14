"""python analysis/run_design_sweep.py — complete, deterministic offline pipeline."""
import sys
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
from pathlib import Path
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import csv
import json
import shutil
import platform
import zipfile
from datetime import datetime, timezone
import numpy as np
from analysis.geometry import ROOT, LEGACY, PAIRS, load_part, load_tool, rim_contacts, mesh_json, sha256
from analysis.lattice import base_network
from analysis.candidates import DESIGNS, PARAMETERS, make_design
from analysis.solver import solve_design, DEFAULTS
from analysis.export_stl import export_design, manufacturing_metrics
from analysis.scoring import score, WEIGHTS


def serializable(value):
    if isinstance(value, np.ndarray): return value.tolist()
    if isinstance(value, np.generic): return value.item()
    if isinstance(value, Path): return str(value)
    raise TypeError(type(value).__name__)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=serializable, allow_nan=False), encoding='utf-8')


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def export_data(part, tool, design, result, mesh, destination):
    lattice = design['lattice']; nodes = result['nodes']; edges = result['edges']
    wire = []
    for k, (a, b) in enumerate(edges):
        wire.append(dict(flat=np.r_[nodes[a], 0., nodes[b], 0.].tolist(), formed=result['formed_nodes'][[a, b]].reshape(-1).tolist(),
                         demand=float(result['edge_strain'][k]), width=float(lattice['width'][k]),
                         compliance=float(lattice['compliance_factor'][k]), parent=int(lattice['parent'][k]),
                         kind=lattice['kinds'][k]))
    cells = []
    for i, (original, candidate) in enumerate(zip(part.cells, design['holes'])):
        cells.append(dict(id=i, original=np.array(original.exterior.coords).tolist(), candidate=np.array(candidate.exterior.coords).tolist(),
                          original_hole_size=float(design['original_hole_size'][i]), hole_size=float(design['hole_size'][i]),
                          baseline_demand=float(design['baseline_cell_demand'][i]),
                          candidate_demand=float(result['parent_demand'][design['cell_parent_indices'][i]].max()),
                          original_ligament_width=float(design['original_cell_width'][i]),
                          ligament_width=float(design['candidate_cell_width'][i])))
    def svg_polygon(poly):
        lines = [poly.exterior, *poly.interiors]
        return ' '.join('M' + ' L'.join(f'{x:.4f},{-y:.4f}' for x, y in ring.coords) + ' Z' for ring in lines)
    footprint = design['material'].union(part.rim_polygon)
    footprint_path = ' '.join(svg_polygon(poly) for poly in (footprint.geoms if hasattr(footprint, 'geoms') else [footprint]))
    content = dict(id=design['id'], part=part.id, lamp=mesh_json(mesh), tool=mesh_json(tool['mesh']), edges=wire,
                   cells=cells, metrics=result['metrics'], validation=result['validation'], score=result['score'],
                   changed_edges=design['changed_edges'], node_count=len(nodes), parent_count=len(result['parent_demand']), footprint_svg=footprint_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(content, ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf-8')


def report(catalog):
    lines = ['# LampForm Lab v0.4 — Design sweep', '',
             f"Gerado em {catalog['generated_at']}. Pipeline offline; o site publica dados e arquivos estáticos.", '',
             '## Baseline reproduzido', '',
             'Os scripts v0.1 e v0.2 foram executados integralmente em `artifacts/baseline`, sem editar `legacy/`. '
             'Todos os quatro baselines convergiram. Diferença máxima <0,02 ponto percentual versus o arquivo fornecido. '
             'Dados detalhados: `generated/baseline_reproduction.json`.', '',
             'A comparação abaixo utiliza um **novo baseline v0.4** calculado pelo mesmo modelo dos candidatos. '
             'Não se comparam números antigos da v0.2 com números novos de candidatos. Os cantos coincidentes são unidos '
             'com tolerância de 0,03 mm e as ligações ao aro são explícitas e verificadas no material.', '',
             '## Candidate generation', '',
             '- **Original:** cópias binárias exatas dos dois STL; paredes medidas em seções transversais do footprint.',
             '- **Gradient:** mesmos centros e pitch nominal; abertura reduzida em até 10%, com suavização espacial de 12 mm do campo baseline.',
             '- **Gradient Boundary:** núcleo do gradiente reduzido a 90% para reservar uma faixa de transição; '
             'pontes em S de 0,95 mm ligam os mesmos locais do aro. O pitch do núcleo passa de 8,0 para 7,2 mm. '
             'Essa mudança de pitch faz parte do candidato, e seu efeito não é isolado do efeito da borda.',
             '- **Compliant:** somente ligamentos interiores acima do percentil 75 de demanda baseline recebem uma onda S de amplitude 0,65 mm e largura 0,95 mm.', '',
             'Os candidatos reconstroem a região plana com a altura detectada de 1 mm; pequenos chanfros da malha original '
             'são aproximados por extrusão constante. O sólido original do aro, com altura de 4 mm e suas interfaces, '
             'é preservado integralmente por união booleana. Mold e Push nunca são modificados.', '',
             '## What we model', '',
             '- Rede de caminhos materiais, comprimentos de repouso, larguras relativas e nós sobre a superfície superior real do STL da ferramenta.',
             '- Caminhos curvos explicitamente segmentados; o comprimento adicional existe tanto no solver quanto no STL.',
             '- Mesma ancoragem 2,0 nos endpoints junto ao aro, mesma penalização interior e mesma sequência de carga 25/50/75/100% para todos os designs.', '',
             '## What we approximate', '',
             'Energia axial proporcional a `(w/w0) * (L/Lref) * strain²`. A propriedade `axial_stiffness_proxy` '
             'é `(w/w0)*(Lref/L)`, um proxy relativo de EA/L. A propriedade `bending_stiffness_proxy` '
             'é `(w/w0)^3*(Lref/L)^3`; a penalização angular usa `(w/w0)^3*(Lref/Ldual)` e peso 0,01. '
             'A altura é a mesma em todas as peças e está registrada por segmento. O material não tem módulo físico atribuído.', '',
             '`compliance_factor` registra comprimento do caminho / distância entre endpoints. '
             'Não se aplica um desconto adicional de rigidez por esse fator: a subdivisão já representa o caminho, evitando dupla contagem.', '',
             'Cada ligamento físico contribui **uma vez** aos percentis, com a maior demanda positiva dos seus segmentos. '
             'As pontes junto ao aro entram nas métricas; não se ocultam seus picos. Isso impede que uma curva com mais nós dilua o score. '
             'A compressão segmentar permanece nos CSV, mas as métricas de demanda usam a parte positiva.', '',
             'As soluções são mínimos locais numéricos da energia proxy. Término por tolerância não prova ótimo global, '
             'e o envelope triangular pode gerar não suavidade. Os arquivos registram custo, critério de parada e optimality para cada etapa.', '',
             '## What we do not model yet', '',
             'Temperatura, PETG/PLA constitutivo, viscoelasticidade, anisotropia de impressão, flambagem, dano/ruptura, '
             'atrito, espessamento/afinamento real e contato bilateral molde–punção. O aro sólido não é deformado por uma malha volumétrica. '
             'Não é FEA termomecânico calibrado. Não há garantia de que pontes terão o mesmo movimento no experimento.', '',
             '## Comparison', '',
             '| Design | Peça | P95 % | Máx. % | >20% | Área aberta % | Material mm² | Score |',
             '|---|---|---:|---:|---:|---:|---:|---:|']
    for d in catalog['designs']:
        for key in ['hab2', 'submerged']:
            m = d[key]['metrics']
            lines.append(f"| {d['name']} | {key} | {m['p95']:.3f} | {m['maximum']:.3f} | {m['above_20_pct']:.2f}% | {m['open_area']:.2f} | {m['material_area_proxy']:.2f} | {d[key]['score']['value']:.4f} |")
    lines += ['', '## Score e recomendação', '',
              '`score = 0.35*(P95/P95₀) + 0.25*(max/max₀) + 0.15*(std/std₀) + '
              '0.15*(material/material₀) + 0.10*(1 + max(0,(open₀-open)/open₀))`.', '',
              'Menor é melhor. Original = 1. Score combinado = média aritmética das duas peças, com pesos iguais. '
              'Material é área projetada sólida; massa é um proxy de volume, sem densidade assumida. '
              'Não é uma medida de resistência. Todos os componentes e diferenças percentuais estão nos JSON.', '',
              f"Menor score combinado: **{catalog['recommendation']['overall_name']}**. "
              f"Melhor alternativa nova para confronto experimental: **{catalog['recommendation']['candidate_name']}**.",
              catalog['recommendation']['reason'], '', '## STL validation', '',
              '| Design | Peça | Watertight | Corpos | Faces degeneradas | Duplicadas | Dimensões mm |',
              '|---|---|---|---:|---:|---:|---|']
    for d in catalog['designs']:
        for key in ['hab2', 'submerged']:
            v = d[key]['validation']
            lines.append(f"| {d['id']} | {key} | {v['watertight']} | {v['body_count']} | {v['degenerate_faces']} | {v['duplicate_faces']} | {' × '.join(f'{x:.3f}' for x in v['dimensions'])} |")
    lines += ['', 'Os originais fornecidos contêm 503 faces duplicadas por peça e não passam no fechamento de malha. '
              'São preservados como solicitado e identificados na interface. Os seis STL candidatos devem ser fechados, '
              'de corpo único, sem duplicadas/degeneradas e reabrir com dimensões dentro de 0,02 mm do original. '
              'Os sólidos novos são extrusões de polígonos válidos unidas com Manifold; '
              'o relatório não apresenta watertight isoladamente como prova de ausência de auto-interseção.', '',
              'A largura mínima é verificada nos caminhos estruturais e não equivale a uma análise de todo canto/chanfro. '
              'Geometria imprimível não garante bom comportamento térmico nem sucesso com qualquer perfil de impressora.', '',
              '## Physical validation plan', '',
              '1. Abrir os dois STL do pacote no slicer, confirmar dimensões e apoio plano, e revisar as camadas.',
              '2. Imprimir Original e a alternativa escolhida com material, orientação e configurações iguais.',
              '3. Usar o mesmo procedimento térmico e a mesma ferramenta correspondente a cada metade.',
              '4. Marcar referências; fotografar e medir deslocamentos, aberturas, afilamento e ruptura.',
              '5. Comparar contra as tendências previstas e calibrar os pesos antes de interpretar valores como deformação física.', '',
              '## Referências de implementação', '',
              '- [SciPy least_squares](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html)',
              '- [Trimesh: extrusão de polígonos](https://trimesh.org/trimesh.creation.html)',
              '- [Manifold: operações booleanas em sólidos](https://github.com/elalish/manifold)', '']
    (ROOT / 'docs/DESIGN_SWEEP_REPORT.md').write_text('\n'.join(lines), encoding='utf-8')


def main():
    hashes = {p.name: sha256(p) for p in LEGACY.glob('*.stl')}
    all_results = {id: dict(id=id, name=name) for id, name in DESIGNS}
    metadata = {}
    for spec in PAIRS:
        part = load_part(spec); tool = load_tool(spec); base = base_network(part.centers)
        contacts = rim_contacts(part, base['nodes'], base['boundary'])
        baseline = None
        for id, name in DESIGNS:
            print(f'{part.name} / {name}: generating geometry', flush=True)
            design = make_design(part, base, contacts, id, baseline)
            folder = ROOT / 'generated' / id; folder.mkdir(parents=True, exist_ok=True)
            mesh, validation = export_design(part, design, folder / f'{part.name}.stl')
            print(f'{part.name} / {name}: solving {len(design["lattice"]["nodes"])} nodes', flush=True)
            result = solve_design(part, tool, design['lattice'])
            if not result['solver']['success']:
                raise RuntimeError(f'{part.name}/{id}: solver did not reach its stopping tolerance')
            result['metrics'].update(manufacturing_metrics(part, design, mesh))
            if id == 'original':
                baseline = result
                design['baseline_cell_demand'] = result['parent_demand'][base['cell_edges']].max(axis=1)
            result['score'] = score(result['metrics'], baseline['metrics'])
            result['validation'] = validation
            dataset = f'data/designs/{id}/{part.id}.json'
            export_data(part, tool, design, result, mesh, ROOT / 'dist' / dataset)
            write_json(folder / f'{part.id}_result.json', result)
            lattice = design['lattice']
            write_json(folder / f'{part.id}_lattice.json', lattice)
            rows = [dict(edge=i, parent=int(lattice['parent'][i]), node_i=int(a), node_j=int(b),
                         rest_length=float(lattice['rest_length'][i]), ligament_width=float(lattice['width'][i]),
                         thickness=float(lattice['thickness'][i]), axial_stiffness_proxy=float(lattice['axial_stiffness_proxy'][i]),
                         bending_stiffness_proxy=float(lattice['bending_stiffness_proxy'][i]), compliance_factor=float(lattice['compliance_factor'][i]),
                         boundary_factor=float(lattice['boundary_factor'][i]), demand_pct=float(result['edge_strain'][i]), kind=lattice['kinds'][i])
                    for i, (a, b) in enumerate(lattice['edges'])]
            write_csv(folder / f'{part.id}_ligaments.csv', rows)
            write_csv(folder / f'{part.id}_cells.csv', [dict(cell=i, x=float(p[0]), y=float(p[1]),
                original_hole_size=float(design['original_hole_size'][i]), candidate_hole_size=float(design['hole_size'][i]),
                baseline_demand=float(design['baseline_cell_demand'][i])) for i, p in enumerate(design['cell_centers'])])
            all_results[id][part.id] = dict(metrics=result['metrics'], score=result['score'], validation=validation,
                                           solver=result['solver'], data=dataset, changed_edges=len(design['changed_edges']),
                                           nodes=len(lattice['nodes']), contacts=len(contacts),
                                           stl=f'downloads/{id.replace("_", "-")}/{part.name}.stl')
            print(f'{part.name} / {name}: P95={result["metrics"]["p95"]:.3f}%, max={result["metrics"]["maximum"]:.3f}%, score={result["score"]["value"]:.4f}', flush=True)
        metadata[part.id] = dict(thickness=part.thickness, rim_height=part.rim_height, pitch=base['pitch'],
                                 core_nodes=len(base['nodes']), core_edges=len(base['edges']), contacts=len(contacts))
    for id, _ in DESIGNS:
        item = all_results[id]
        item['combined_score'] = np.mean([item[k]['score']['value'] for k in ['hab2', 'submerged']]).item()
        item['combined_improvement_pct'] = 100 * (1 - item['combined_score'])
        item['zip'] = f'downloads/lampform-{id.replace("_", "-")}.zip'
        folder = ROOT / 'dist/downloads' / id.replace('_', '-'); folder.mkdir(parents=True, exist_ok=True)
        metrics = {k: {field: item[k][field] for field in ['metrics', 'score', 'validation', 'solver']} for k in ['hab2', 'submerged']}
        write_json(folder / 'metrics.json', metrics)
        write_json(folder / 'parameters.json', dict(design=id, geometry=PARAMETERS, solver=DEFAULTS, source_hashes=hashes))
        for _, part_name, _, _ in PAIRS: shutil.copyfile(ROOT / 'generated' / id / f'{part_name}.stl', folder / f'{part_name}.stl')
        (folder / 'README.txt').write_text(f'LampForm Lab v0.4 / {id}\nUnits: mm. Flat pieces; lattice 1 mm, rim 4 mm.\n'
            'HAB-2 -> Mold; Sub-Merged -> Push. Tools are unchanged.\n'
            'Open both STL in a slicer and inspect layers before printing.\n'
            'Relative geometric/structural demand, NOT calibrated polymer strain.\n'
            'Parameters, convergence and mesh checks are in the accompanying JSON files.\n'
            + ('Original source STL retained unchanged; duplicate faces and non-watertight input require slicer review.\n' if id == 'original' else
               'Candidate geometry reloaded and checked closed, single body, with no duplicate or degenerate faces.\n'), encoding='utf-8')
        with zipfile.ZipFile(ROOT / 'dist' / item['zip'], 'w', zipfile.ZIP_DEFLATED) as z:
            for path in sorted(folder.iterdir()): z.write(path, arcname=path.name)
    items = list(all_results.values())
    overall = min(items, key=lambda d: d['combined_score'])
    candidate = min(items[1:], key=lambda d: d['combined_score'])
    reason = (f'{candidate["name"]} tem o menor score combinado entre as alternativas novas ({candidate["combined_score"]:.3f}). '
              + ('O Original ainda tem menor score; nenhum novo design demonstrou vantagem global nesta rodada.' if overall['id'] == 'original' else
                 'A vantagem é apenas prevista pelo modelo e depende de validação física.'))
    for part_id, part_name, _, _ in PAIRS:
        delta = 100 * (candidate[part_id]['metrics']['maximum'] / items[0][part_id]['metrics']['maximum'] - 1)
        if delta > 0:
            reason += f' Atenção: o pico de demanda em {part_name} aumenta {delta:.1f}% frente ao Original.'
    catalog = dict(version='0.4.0', generated_at=datetime.now(timezone.utc).isoformat(), python=platform.python_version(),
                   source_hashes=hashes, geometry=metadata, score_weights=WEIGHTS,
                   common_color_ranges=dict(demand=[0, 180], width=[.8, 4], hole_size=[4, 7.1], compliance=[1, 1.5]),
                   recommendation=dict(overall_id=overall['id'], overall_name=overall['name'],
                       candidate_id=candidate['id'], candidate_name=candidate['name'], beats_original=overall['id'] != 'original', reason=reason),
                   designs=items)
    write_json(ROOT / 'dist/data/designs.json', catalog)
    write_json(ROOT / 'generated/designs.json', catalog)
    report(catalog)
    from analysis.render_report import render_report
    render_report(catalog)
    if hashes != {p.name: sha256(p) for p in LEGACY.glob('*.stl')}: raise RuntimeError('Original STL was modified')
    print('\nDesign sweep complete.', flush=True)
    for d in items: print(f'{d["name"]} score: {d["combined_score"]:.4f}')
    print(f'Recommended candidate: {candidate["name"]}\n{reason}\nGenerated: dist/data/designs.json and dist/downloads/...')


if __name__ == '__main__':
    raise SystemExit('v0.4 command retired to protect v0.5 exports. Use python analysis/build_design_space.py. Shared export helpers remain importable.')
