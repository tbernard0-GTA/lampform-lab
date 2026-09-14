# LampForm Lab v0.6 — Physical Validation Loop

## Problema e escopo

A falha durante termoformação é o problema relatado pelo autor. Esta versão prepara um experimento que pode refutar o modelo: prever regiões de maior deformação, fabricar alterações controladas, medir e comparar. Não existem medições físicas nesta entrega. Não se afirma que uma nova topologia resolveu a falha.

A v0.5 é preservada no commit `6f7215aafdc75ae070fb3aa1d3ddded3cdbdac7f`, no catálogo anterior e em `workbench-v05.html`. HAB-2 e Sub-Merged têm escolhas independentes. Atualmente ambas recebem Reserve Search 3 pelo menor índice de risco entre os candidatos que passam nos gates individuais; isso decorre dos resultados, não de uma obrigação do configurador.

## Geometria e solver

Os quatro STL fornecidos e os scripts históricos permanecem em `legacy/`. O solver usa o envelope da superfície real da ferramenta, deslocamentos XY, demanda axial relativa, rigidez relativa pela largura, penalidade angular e restrição periférica. As cinco etapas exibidas são o estado plano e quatro soluções de continuação. As cores de demanda indicam o resultado final em todas as etapas.

Não são resolvidos tensão calibrada do polímero, campo térmico, E(T), viscoelasticidade, creep, contato com atrito, anisotropia entre camadas, deformação real de ruptura ou dano. O sólido real é mostrado no estado plano; Formed mostra a rede equivalente.

## Campo local: F, λ1, λ2 e direções

Cada uma das 65 células usa os mesmos seis nós de referência em todos os designs. IDs H001–H065 e S001–S065 acompanham geometria, solver e medição. Nós adicionados dentro de caminhos ondulados não alteram essa correspondência.

1. Centralizar as posições planas X (n × 2) e formadas Y (n × 3).
2. Ajustar o plano tangente por PCA/SVD das posições Y; a normal é o vetor de menor variância.
3. Construir uma base tangente ortonormal T (2 × 3) e projetar Z = Y Tᵀ.
4. Resolver por mínimos quadrados X Fᵀ ≈ Z.
5. Decompor F = U diag(λ1, λ2) Vᵀ, com λ1 ≥ λ2. As linhas de Vᵀ são as direções materiais em XY; Tᵀ U dá as direções formadas em 3D.

J = λ1 λ2 aproxima a expansão de área; λ1/λ2 descreve anisotropia geométrica. São medidas de um ajuste celular, não propriedades constitutivas. A implementação segue a convenção de [SVD do NumPy](https://numpy.org/doc/stable/reference/generated/numpy.linalg.svd.html).

Guardamos F, base tangente, normal, RMS do ajuste, RMS fora do plano e determinante com sinal. Um resíduo relativo >20% ou det(F) ≤0 gera aviso. No Original, o maior RMS afim é aproximadamente 1,765 mm no HAB-2 e 1,215 mm no Sub-Merged: algumas células não admitem interpretação afim precisa. J positivo por SVD não deve ocultar inversões; por isso o determinante também é guardado.

As setas mostram ±d1 e comprimento proporcional a |λ1−1|. Quando λ1/λ2 ≤1,02, a direção é pouco determinada e a seta é omitida na bancada. Nos mapas impressos, a linha azul ainda fornece uma orientação de referência convencional; não implica uma direção física resolvida.

## Classificação de mecanismo

É uma heurística de projeto. Os limiares ficam em `analysis/local_deformation.py` e no pacote:

| Categoria | Regra inicial |
|---|---|
| Directional compliance | λ1/λ2 ≥1,15 |
| Area expansion | λ2 >1,04 e J >1,20 |
| Boundary feed | célula periférica, XY >2 mm e sensibilidade periférica absoluta >1 p.p. |
| Material reserve | demanda de ligamento >30% e XY <2 mm |
| Mixed | várias regras ou demanda sem mecanismo isolado |
| Low demand | nenhuma regra, λ1 <1,10 e demanda <10% |

A sensibilidade de borda é uma solução adicional real do Original com boundary_anchor reduzido de 2 para 1. Só Original/A recebe essa informação. Nos demais candidatos, ausência de sensibilidade é declarada; não se inventa a categoria Boundary feed. Clicar numa célula mostra valores, classificação e motivo.

## Matriz causal e reparo

ORIGINAL_* preserva os defeitos topológicos fornecidos. Para comparação física, A e *_original_repaired_for_test reconstroem a extrusão de 1 mm da pegada nominal e fazem união Manifold com o aro original de 4 mm. O padrão nominal permanece; a tolerância de exportação é 0,0001 mm. Use A reparado como controle para evitar comparar um sólido íntegro com uma malha defeituosa.

| Teste Sub-Merged | Núcleo | Transição para o aro |
|---|---|---|
| A | Original | Original |
| B | Reserva: aberturas internas com escala 0,965 | Original |
| C | Original | Dois conectores longos em S |
| D | Igual a B | Igual a C |

A máscara protegida inclui células e caminhos do núcleo. C mantém pitch, posições dos 162 nós do núcleo, geometria das aberturas e material do núcleo: diferença de área protegida = 0. Os 20 caminhos de contato são iguais entre A/B e entre C/D. Apenas dois conectores de aproximadamente 7,7 mm dispõem de região livre suficiente para a alteração C: amplitude 0,25 mm, largura 1 mm. Os outros 18 permanecem iguais. C testa uma intervenção periférica limitada, não uma borda inteiramente flexível.

B acrescenta aproximadamente 105,780768 mm² na máscara do núcleo. D acrescenta 105,780761 mm²: diferença numérica inferior a 0,00001 mm². O teste automático usa tolerância de 0,0001 mm². O aro permanece preservado.

Dois conceitos adicionais geram STL reais: ligamentos em S alinhados com d1, e ligamentos ondulados em mais de uma orientação onde J é elevado. Ambos usam amplitude 0,4 mm, largura 1 mm e caminhos não adjacentes selecionados. O segundo é um conceito cinemático bidirecional, não uma estrutura auxética comprovada.

## Resultados atuais: hipótese, não vencedor

Demanda de ligamento em %, no Sub-Merged. Todos convergiram; sete STL novos (incluindo A/HAB-2) passaram nos checks geométricos de exportação, com um corpo fechado.

| Design | P95 | P99 | Máximo | Ligamentos >30% |
|---|---:|---:|---:|---:|
| A / Original | 55,475 | 70,124 | 83,855 | 98 |
| B / Reserve only | 60,095 | 83,338 | 95,592 | 92 |
| C / Boundary only | 67,209 | 88,050 | 196,854 | 97 |
| D / Hybrid | 73,716 | 97,880 | 169,938 | 101 |
| Directional S | 69,501 | 88,069 | 107,106 | 101 |
| Bidirectional undulating | 65,315 | 84,055 | 101,118 | 105 |

B/C/D não passam como melhorias. C e D concentram demanda muito alta em regiões do modelo. Esses resultados permanecem visíveis: é preciso testar a hipótese, em vez de escolher pelo aspecto visual. Os checks de STL não garantem imprimibilidade de cada detalhe nem bom comportamento durante aquecimento. Inspeção de camadas continua necessária.

## Medição e comparação

O plano seleciona 20 células por peça, distribuídas entre faixas de demanda, borda e interior. Grupos sem células não são preenchidos artificialmente. O template A/B/C/D tem 80 linhas planejadas, sem qualquer medida ou condição térmica inventada.

Antes de formar, definir dois segmentos materiais alinhados com d1/d2 e marcar seus extremos. Medir os mesmos pontos depois, sem reordenar L1/L2 pelo maior comprimento observado. λ1_medido = L1_depois/L1_antes; λ2_medido = L2_depois/L2_antes; J_medido é o produto. Essas razões ao longo de eixos materiais são proxies das extensões principais; cisalhamento, rotação dos eixos e curvatura limitam a comparação. Registrar método e fotos com escala. Não confundir comprimento curvo de um ligamento com corda da célula.

Importação CSV/JSON e formulário funcionam localmente. Cada observação exige experiment_id/sample_id, peça, design e célula válida. Medidas são quatro valores positivos ou quatro campos vazios. Uma ocorrência de falha pode existir sem medidas. Duplicatas e condições de processo conflitantes dentro da amostra são rejeitadas. Exportar antes de fechar: os dados não são persistidos nem enviados ao servidor.

Os mapas comparam 100(λ1−1) previsto/medido. Erro = medido − previsto, em pontos percentuais. Valores ausentes ficam cinza. Spearman usa postos médios para empates e só é apresentado com ≥3 pares não constantes. Top-K usa K = min(10, max(1, floor(n/3))) para evitar selecionar todas as observações; empates na fronteira têm participação fracionária. Hotspot precision/recall usa demanda prevista de ligamento >30% contra failure explícito. Sem denominador, mostra ausência, não zero.

## Processo, calibração e validação

O procedimento de 14 passos está no ZIP. Registrar material/lote, perfil de impressão, equipamento/potência/distância de aquecimento, temperatura superficial, tempos de formar/manter/resfriar e método de medição. O cartão térmico documenta condições reais; não acrescenta temperatura ao solver. Sensores opcionais usam time_s, displacement_mm, force_n, temperature_c; gráficos só aparecem com pares válidos.

A calibração offline exige ≥5 células medidas em uma amostra Original e ≥5 em uma Candidate distinta da mesma peça. Nove configurações limitadas exploram boundary_anchor (1/3), bending_weight (0,005/0,02) e interior_anchor (0,00025/0,001), além do default. A escala axial fica fixa porque a rigidez absoluta não é identificável neste experimento geométrico.

Minimiza-se o RMS de diferenças de postos normalizados na calibração. Só soluções convergidas e com correlação definida podem vencer. Candidate só é avaliada após congelar os parâmetros. O relatório separa ajuste e validação, registra hashes dos dados e solver, e mantém previsões base intactas no site. Não houve ajuste a medidas físicas nesta versão. Separação de datasets no software não substitui um protocolo realmente cego e réplicas independentes.

## Story Mode e próximo ensaio

As 12 cenas percorrem objeto, problema, ferramentas, reconstrução, formação, extensões principais, mecanismos, Original, resposta geométrica, delta, limites da simulação e ciclo físico. Usam os mesmos dados da bancada. Metadados de câmera e narração estão em `story/storyboard.json`; roteiro em `VIDEO_STORYBOARD.md`. `npm run capture-story` produz 12 frames de 1920 × 1080 em `docs/video_frames/`. São composições offline dos mesmos datasets, não capturas pixel a pixel do navegador.

Próximo passo físico: revisar camadas e imprimir A/B/C/D do Sub-Merged sob condições equivalentes, registrar o processo e medir o plano proposto. HAB-2 pode receber Original reparado versus Reserve Search 3 como ensaio adicional independente. Nenhuma impressão ou termoformação foi iniciada pelo aplicativo.
