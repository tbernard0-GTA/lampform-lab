# Verificação v0.6 — Physical Validation Loop

Revisão concluída em 14 de setembro de 2026, antes da publicação para avaliação do autor.

- `npm test`: 36 testes JavaScript e 12 Python passaram. Incluem reprodução anterior, geometria/STL, correspondência dos dados, ajuste afim sob rotação e extensões conhecidas, isolamento de A/B/C/D, IDs, template vazio, correlação/empates, rejeição de duplicatas e separação de amostras.
- `npm run build`: bundles da bancada e Story Mode gerados sem erros. Auditoria das dependências: zero vulnerabilidades na versão instalada.
- Os sete novos STL são sólidos fechados de um corpo nos checks de exportação. Núcleo A/C idêntico; B/D equivalente dentro da tolerância; contatos A/B e C/D preservados. Nenhum teste físico foi executado.
- Template real de 80 células importado no navegador: permanece sem medidas e sem correlação. Uma fixture matemática descartável, explicitamente identificada como software QA e fora da pasta pública, verificou importação JSON, erro zero, Spearman 1 e Top-2 100%. Isso verifica software, não previsão física. Entrada manual de ocorrência sem comprimentos também foi verificada.
- Exportação de trabalho de calibração funcionou; reusar a mesma amostra para ambos os papéis foi rejeitado. Nenhum ajuste com dados físicos está incluído. A calibração offline ainda precisará ser exercitada com medições reais e condições repetíveis.
- Downloads verificados: ZIP físico íntegro com 26 arquivos; ZIP combinado baixado contém os dois STL escolhidos independentemente, com bytes iguais aos arquivos do catálogo. Nenhuma fixture de QA está no conteúdo público.
- Story Mode 01–12 foi percorrido na revisão anterior à pausa. Após os ajustes finais, cenas 01, 06/capture, 09/borda e 12/sem dados foram revisitadas. A captura pelo navegador gerou PNG válido em 1920×1080; o script offline gerou os 12 frames nessa resolução, com revisão visual de quadros principais.
- Workbench foi revisado em desktop: ferramenta STL real, rede formada, etapas, λ1/λ2/J/risco, mecanismo por célula, navegação por teclado, diferença geométrica exata e zoom da borda C. Print apresenta A/B/C/D e suas diferenças.
- Layout a 390×844: Print, Deformation, Experiment e Calibration sem transbordamento horizontal da página. A matriz de impressão tem rolagem horizontal própria.

Os resultados negativos de B/C/D permanecem publicados como hipóteses experimentais. Convergência e STL válido não demonstram melhoria física. Não houve nova inspeção de camadas desses sete STL na interface do Cura. A inspeção e o ensaio físico continuam sendo etapas de bancada.

## Registro preservado: bancada v0.5

Atualização para validação pelo autor: 14 de setembro de 2026.

- Originais e ferramentas preservados em `legacy/`. Baselines v0.1/v0.2 reproduzidos, com diferenças inferiores a 0,02 ponto percentual (`generated/baseline_reproduction.json`).
- Treze designs calculados com o mesmo solver, incluindo Original; 26 conjuntos de resultados, cinco etapas reais de continuação e 24 STL candidatos novos.
- Testes verificam correspondência entre campos, métricas, geometria e arquivos; gates das duas peças; hashes dos downloads; sólidos fechados com um corpo; preservação do aro; largura dos caminhos; conteúdo dos ZIP. Uma ablação confirma que a largura afeta a solução.
- CuraEngine 5.9.0 processou Original e Reserve Search 3 nas duas peças, com 20 camadas e sem avisos registrados. Resultados e hashes estão em `generated/slicer_validation.json`. Isso não substitui inspeção visual das camadas nem validação física.
- A bancada v0.5 foi vista no navegador em desktop: geometrias STL e rede conformada carregaram. A inspeção visual completa dos controles e do layout móvel permanece pendente.
- A inspeção final dos STL Reserve Search 3 na interface do Cura foi interrompida. A versão atual foi publicada a pedido do autor para sua validação, antes dessa conclusão.

## Limites da recomendação

Reserve Search 3 passa nos critérios relativos das duas peças. No Sub-Merged, os ligamentos críticos caem apenas de 98 para 97 e o pico aumenta 0,78 ponto percentual: a margem é pequena. A recomendação é de teste físico, sem demonstração de robustez.

Não houve impressão física, calibração de polímero, análise térmica ou validação de ruptura. Os estados conformados mostram a rede equivalente do solver, não um novo sólido deformado. As cores de demanda usam o resultado final em todas as etapas.
