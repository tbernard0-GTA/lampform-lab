# LampForm Lab v0.8 — Parametric Lattice Design Lab

[A história](https://lampform-lab.oieszc.chatgpt.site) · [Design Lab](https://lampform-lab.oieszc.chatgpt.site/design/) · [STLs e mapas V2](https://lampform-lab.oieszc.chatgpt.site/downloads/LAMPFORM_PARAMETRIC_TEST_V2.zip)

A página inicial conta a pesquisa em sete capítulos. O laboratório separa os controles avançados e oferece 48 configurações calculadas: Honeycomb, Triangle e Diamond, comparação por volume equivalente e um experimento de largura versus altura para as duas peças.

Cada seleção corresponde a uma geometria, solver e STL reais. Os controles ajustam explicitamente a seleção ao catálogo disponível; não existe interpolação de métricas ou execução do solver no navegador. A adaptação local está disponível em Honeycomb. Triangle e Diamond têm estados uniformes e de volume equivalente.

O pacote V2 tem A uniforme, B largura variável, C altura variável e D ambas, por peça. Alturas em passos de 0,1 mm; B/C/D usam aproximadamente +10% de volume da malha. São hipóteses para ensaio, sem comprovação física. A altura variável não melhora todos os resultados.

Regenerar: `npm run analysis:parametric` com o ambiente Python ativado; depois `npm run build` e `npm test`. O script BUILD inclui todas as análises. [Método v0.8](docs/V08_IMPLEMENTATION_NOTES.md) · [Resultados completos](docs/V08_CALCULATED_CATALOG.md).

## Referência preservada: v0.6 — Physical Validation Loop

[Aplicação pública](https://lampform-lab.oieszc.chatgpt.site) · [Story Mode](https://lampform-lab.oieszc.chatgpt.site/story.html?scene=01) · [Método e resultados v0.6](docs/LAMPFORM_V06_PHYSICAL_VALIDATION.md) · [Storyboard](docs/VIDEO_STORYBOARD.md)

Uma bancada para prever, fabricar, medir e comparar uma luminária impressa plana e termoformada. Não existem medições físicas ou calibração do polímero nesta versão.

## Novidades v0.6

Geometry → Deformation → Mechanisms → Design → Compare → Experiment → Calibration → Print. Inspecione λ1, λ2, J, anisotropia e direções por célula. Use Change only e Zoom da alteração para examinar os novos testes. HAB-2 e Sub-Merged têm escolhas independentes e podem ser baixadas juntas num ZIP.

Print oferece A/B/C/D do Sub-Merged, com STL reais, plano de 20 células por peça, template e procedimento. B/C/D investigam mecanismos; não melhoram o P95 no modelo atual. Os originais fornecidos e os reparados têm arquivos separados.

Experiment aceita CSV/JSON e entrada manual. Os dados ficam na memória deste navegador; exporte antes de fechar ou recarregar. Valores ausentes permanecem ausentes. A calibração usa Original e uma amostra Candidate separada da mesma peça.

Story Mode tem 12 cenas. Setas e Space navegam; Esc volta à bancada. Abra `story.html?scene=06` ou `story.html?scene=06&mode=capture` para gravação limpa em 16:9. Capture frame exporta a cena atual; `npm run capture-story` gera as 12 imagens offline em `docs/video_frames/`, com os mesmos dados e composição própria.

O site compilado e os resultados já estão incluídos. `npm start` ou `PLAY-LAMPFORM-LAB.cmd` abre localmente. Depois de instalar as dependências abaixo, a geração completa usa:

```powershell
.\.venv\Scripts\python.exe analysis/build_design_space.py
.\.venv\Scripts\python.exe analysis/build_physical.py
npm run build
npm test
npm run capture-story
```

`BUILD-LAMPFORM-LAB.cmd` inclui as duas análises. Com o ambiente Python ativado, `npm run analysis:physical` regenera a v0.6. Depois de obter medidas reais, exporte um trabalho na aba Calibration e execute `python analysis/calibrate_physical.py calibration_job.json`. Importe o relatório selecionando os mesmos datasets. Ele não substitui silenciosamente as previsões base.

O catálogo v0.6 usa `dist/data/physical/results.json`. A bancada anterior está preservada em [workbench-v05.html](https://lampform-lab.oieszc.chatgpt.site/workbench-v05.html). O método, limites e resultados negativos estão documentados no relatório v0.6.

## Referência preservada: Engineering Workbench v0.5

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
