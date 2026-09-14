# LampForm Lab — Engineering Workbench v0.5

[Aplicação pública](https://lampform-lab.oieszc.chatgpt.site) · [Relatório de engenharia](docs/LAMPFORM_V05_ENGINEERING_REPORT.md)

Uma bancada visual para investigar uma luminária impressa plana e termoformada. Compare Original e candidatos reais, localize concentração de demanda, veja mudanças geométricas, diferenças e alimentação XY, e baixe o STL exato.

## Uso

Abra o site e selecione HAB-2 ou Sub-Merged, família e intensidade. Os dois viewers compartilham câmera e escala de cores. O mapa plano permite inspecionar células, sobrepor geometrias, mostrar apenas alterações, examinar delta e vetores XY. Danger zones, matriz ordenável e gráficos separam risco de custo de fabricação. Story / About conta o contexto.

Os resultados são calculados offline. O site não executa Python, não recebe uploads e não oferece edição pública. O repositório é público; modificações no repositório principal dependem do proprietário. A visibilidade pública permite leitura e forks conforme as regras do GitHub; não concede acesso de escrita.

## Gerar novamente

Requisitos: Python 3.13+ e Node.js 22+. Dependências científicas fixadas em requirements-analysis.txt.

No Windows: execute BUILD-LAMPFORM-LAB.cmd. Depois use PLAY-LAMPFORM-LAB.cmd para abrir localmente.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-analysis.txt
npm ci
.\.venv\Scripts\python.exe analysis/build_design_space.py
npm run build
npm test
npm start
```

Com o ambiente Python ativado, o comando principal é `python analysis/build_design_space.py`. A pipeline anterior permanece disponível em `python analysis/run_design_sweep.py` e gera o catálogo v0.4 separado.

O modo opcional `--reuse-solutions` reaproveita soluções somente se coordenadas, arestas, larguras, comprimentos, ancoragens, parent IDs, parâmetros do solver e hash do STL coincidirem. O modo padrão recalcula tudo.

## Modelo e gates

Dez designs iniciais: Original e três intensidades de Reserve, Boundary e Hybrid. Se nenhum par passar, até três perturbações adicionais de Reserve são testadas. Cada tentativa fica em generated/sweep/. Sem ML e sem métricas interpoladas.

Risco: 30% P95 + 25% P99 + 25% máximo + 20% fração crítica, normalizados ao Original. Material e área aberta ficam separados. Print gate: P95 menor, menos ligamentos acima de 30%, pico no máximo +5 pontos percentuais, solução convergida e geometria válida. A recomendação exige aprovação das DUAS peças. Nenhum vencedor é inventado se a busca terminar sem aprovação.

## Arquivos

- legacy/: material original preservado, incluindo os quatro STL e os scripts v0.1/v0.2.
- analysis/: geometria, rede estrutural, solver, geração, gates, exportação e relatórios.
- config/manufacturing.yaml: defaults de fabricação (JSON compatível com YAML 1.2).
- generated/baseline_reproduction.json: comparação da reprodução dos scripts originais.
- generated/sweep/: resultados, parâmetros, redes e CSV de todas as tentativas.
- dist/data/results.json: catálogo completo v0.5.
- dist/downloads/: STL e ZIP reais, métricas, parâmetros e instruções.
- web/: fonte do app estático; dist/: versão compilada publicada.

## Limites

É um modelo de demanda geométrica/estrutural relativa, não FEA termomecânico calibrado. Não prevê temperatura, E(T), viscoelasticidade, atrito, anisotropia ou ruptura real. A vista formada é a rede analítica nas etapas calculadas; o STL exato é mostrado plano.

Os STL originais das lâmpadas têm faces duplicadas e não são watertight; são preservados sem reparos. Os candidatos são novos sólidos fechados e mantêm o aro original. Mold e Push nunca são alterados. Os checks de largura cobrem caminhos estruturais e a sonda de abertura cobre células principais; cantos e vãos periféricos devem ser revistos no slicer.

Consulte o relatório para resultados, rejeições, alcance da validação e recomendação física (ou ausência dela).
