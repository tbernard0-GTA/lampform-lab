# LampForm Lab v0.4 — Design sweep

Gerado em 2026-09-14T15:37:15.857506+00:00. Pipeline offline; o site publica dados e arquivos estáticos.

## Baseline reproduzido

Os scripts v0.1 e v0.2 foram executados integralmente em `artifacts/baseline`, sem editar `legacy/`. Todos os quatro baselines convergiram. Diferença máxima <0,02 ponto percentual versus o arquivo fornecido. Dados detalhados: `generated/baseline_reproduction.json`.

A comparação abaixo utiliza um **novo baseline v0.4** calculado pelo mesmo modelo dos candidatos. Não se comparam números antigos da v0.2 com números novos de candidatos. Os cantos coincidentes são unidos com tolerância de 0,03 mm e as ligações ao aro são explícitas e verificadas no material.

## Candidate generation

- **Original:** cópias binárias exatas dos dois STL; paredes medidas em seções transversais do footprint.
- **Gradient:** mesmos centros e pitch nominal; abertura reduzida em até 10%, com suavização espacial de 12 mm do campo baseline.
- **Gradient Boundary:** núcleo do gradiente reduzido a 90% para reservar uma faixa de transição; pontes em S de 0,95 mm ligam os mesmos locais do aro. O pitch do núcleo passa de 8,0 para 7,2 mm. Essa mudança de pitch faz parte do candidato, e seu efeito não é isolado do efeito da borda.
- **Compliant:** somente ligamentos interiores acima do percentil 75 de demanda baseline recebem uma onda S de amplitude 0,65 mm e largura 0,95 mm.

Os candidatos reconstroem a região plana com a altura detectada de 1 mm; pequenos chanfros da malha original são aproximados por extrusão constante. O sólido original do aro, com altura de 4 mm e suas interfaces, é preservado integralmente por união booleana. Mold e Push nunca são modificados.

## What we model

- Rede de caminhos materiais, comprimentos de repouso, larguras relativas e nós sobre a superfície superior real do STL da ferramenta.
- Caminhos curvos explicitamente segmentados; o comprimento adicional existe tanto no solver quanto no STL.
- Mesma ancoragem 2,0 nos endpoints junto ao aro, mesma penalização interior e mesma sequência de carga 25/50/75/100% para todos os designs.

## What we approximate

Energia axial proporcional a `(w/w0) * (L/Lref) * strain²`. A propriedade `axial_stiffness_proxy` é `(w/w0)*(Lref/L)`, um proxy relativo de EA/L. A propriedade `bending_stiffness_proxy` é `(w/w0)^3*(Lref/L)^3`; a penalização angular usa `(w/w0)^3*(Lref/Ldual)` e peso 0,01. A altura é a mesma em todas as peças e está registrada por segmento. O material não tem módulo físico atribuído.

`compliance_factor` registra comprimento do caminho / distância entre endpoints. Não se aplica um desconto adicional de rigidez por esse fator: a subdivisão já representa o caminho, evitando dupla contagem.

Cada ligamento físico contribui **uma vez** aos percentis, com a maior demanda positiva dos seus segmentos. As pontes junto ao aro entram nas métricas; não se ocultam seus picos. Isso impede que uma curva com mais nós dilua o score. A compressão segmentar permanece nos CSV, mas as métricas de demanda usam a parte positiva.

As soluções são mínimos locais numéricos da energia proxy. Término por tolerância não prova ótimo global, e o envelope triangular pode gerar não suavidade. Os arquivos registram custo, critério de parada e optimality para cada etapa.

## What we do not model yet

Temperatura, PETG/PLA constitutivo, viscoelasticidade, anisotropia de impressão, flambagem, dano/ruptura, atrito, espessamento/afinamento real e contato bilateral molde–punção. O aro sólido não é deformado por uma malha volumétrica. Não é FEA termomecânico calibrado. Não há garantia de que pontes terão o mesmo movimento no experimento.

## Comparison

| Design | Peça | P95 % | Máx. % | >20% | Área aberta % | Material mm² | Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Original | hab2 | 35.984 | 64.334 | 61.38% | 66.30 | 1663.97 | 1.0000 |
| Original | submerged | 55.475 | 83.855 | 77.64% | 66.30 | 1663.98 | 1.0000 |
| Gradient | hab2 | 29.613 | 36.979 | 50.00% | 59.31 | 2009.06 | 0.8390 |
| Gradient | submerged | 51.443 | 107.797 | 78.46% | 61.42 | 1905.16 | 1.0913 |
| Gradient + Compliant Boundary | hab2 | 46.805 | 103.375 | 47.56% | 62.35 | 1859.13 | 1.3717 |
| Gradient + Compliant Boundary | submerged | 104.322 | 148.597 | 46.75% | 63.86 | 1784.70 | 1.6494 |
| Compliant | hab2 | 34.237 | 57.833 | 51.63% | 66.14 | 1672.00 | 0.9478 |
| Compliant | submerged | 59.558 | 91.281 | 56.91% | 66.19 | 1669.43 | 1.0739 |

## Score e recomendação

`score = 0.35*(P95/P95₀) + 0.25*(max/max₀) + 0.15*(std/std₀) + 0.15*(material/material₀) + 0.10*(1 + max(0,(open₀-open)/open₀))`.

Menor é melhor. Original = 1. Score combinado = média aritmética das duas peças, com pesos iguais. Material é área projetada sólida; massa é um proxy de volume, sem densidade assumida. Não é uma medida de resistência. Todos os componentes e diferenças percentuais estão nos JSON.

Menor score combinado: **Gradient**. Melhor alternativa nova para confronto experimental: **Gradient**.
Gradient tem o menor score combinado entre as alternativas novas (0.965). A vantagem é apenas prevista pelo modelo e depende de validação física.

## STL validation

| Design | Peça | Watertight | Corpos | Faces degeneradas | Duplicadas | Dimensões mm |
|---|---|---|---:|---:|---:|---|
| original | hab2 | False | 3 | 0 | 503 | 73.294 × 97.073 × 4.000 |
| original | submerged | False | 3 | 0 | 503 | 73.294 × 97.073 × 4.000 |
| gradient | hab2 | True | 1 | 0 | 0 | 73.294 × 97.073 × 4.000 |
| gradient | submerged | True | 1 | 0 | 0 | 73.294 × 97.073 × 4.000 |
| gradient_boundary | hab2 | True | 1 | 0 | 0 | 73.294 × 97.073 × 4.000 |
| gradient_boundary | submerged | True | 1 | 0 | 0 | 73.294 × 97.073 × 4.000 |
| compliant | hab2 | True | 1 | 0 | 0 | 73.294 × 97.073 × 4.000 |
| compliant | submerged | True | 1 | 0 | 0 | 73.294 × 97.073 × 4.000 |

Os originais fornecidos contêm 503 faces duplicadas por peça e não passam no fechamento de malha. São preservados como solicitado e identificados na interface. Os seis STL candidatos devem ser fechados, de corpo único, sem duplicadas/degeneradas e reabrir com dimensões dentro de 0,02 mm do original. Os sólidos novos são extrusões de polígonos válidos unidas com Manifold; o relatório não apresenta watertight isoladamente como prova de ausência de auto-interseção.

A largura mínima é verificada nos caminhos estruturais e não equivale a uma análise de todo canto/chanfro. Geometria imprimível não garante bom comportamento térmico nem sucesso com qualquer perfil de impressora.

## Physical validation plan

1. Abrir os dois STL do pacote no slicer, confirmar dimensões e apoio plano, e revisar as camadas.
2. Imprimir Original e a alternativa escolhida com material, orientação e configurações iguais.
3. Usar o mesmo procedimento térmico e a mesma ferramenta correspondente a cada metade.
4. Marcar referências; fotografar e medir deslocamentos, aberturas, afilamento e ruptura.
5. Comparar contra as tendências previstas e calibrar os pesos antes de interpretar valores como deformação física.

## Referências de implementação

- [SciPy least_squares](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html)
- [Trimesh: extrusão de polígonos](https://trimesh.org/trimesh.creation.html)
- [Manifold: operações booleanas em sólidos](https://github.com/elalish/manifold)
