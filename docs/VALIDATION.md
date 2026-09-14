# Validação da demonstração

Publicação inicial: 14 de setembro de 2026.

- Os 28 arquivos do ZIP são preservados integralmente em `legacy/lampform_lab_v01/`, sem alterações dos scripts ou resultados.
- `scripts/prepare_data.py` exporta quatro STL binários e os CSV da v0.2 para dados de apresentação. Guarda o SHA-256 de cada STL.
- `npm test`: quatro testes verificam hashes, contagem de triângulos, índices, coordenadas finitas, correspondência das métricas, comprimento dos ligamentos e P95 calculado a partir da rede.
- Verificação no navegador: ambas as peças, estados plana/conformada/demanda, ferramenta visível/oculta, extremos do slider, restauração da vista e seleção de ancoragem.
- Na peça Sub-merged, a seleção 0,05 exibe P95 6,2% e redução de 82,2% em relação ao P95 de referência 34,6%, calculados dos valores completos dos CSV.
- Layout conferido em desktop e em viewport de 390 × 844, sem rolagem horizontal.
- A página é servida localmente por HTTP e o JavaScript compilado passou pela verificação de sintaxe.

## Limites

Os solvers legados não foram reexecutados nesta fase. Os testes validam o transporte e a coerência dos resultados fornecidos, não a validade física do modelo. Não se afirma convergência reproduzida nesta publicação, calibração de material, fabricação de candidatos novos ou validação de impressão.

A geometria da peça plana vem do STL. A geometria conformada é uma rede equivalente de eixos dos ligamentos, desenhados com espessura apenas para legibilidade. Não representa uma nova peça sólida pronta para impressão. O movimento intermediário é interpolado e não recalculado pelo solver.
