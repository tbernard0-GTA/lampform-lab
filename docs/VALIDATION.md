# Validação da bancada v0.5

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
