# LampForm Lab v0.1 — drape geométrico da luminária

Este laboratório usa os quatro STL fornecidos para estimar a incompatibilidade geométrica entre as duas peças planas e as superfícies reais das ferramentas de conformação.

## Associação geométrica detectada

- `obj_1_HAB-2.stl` → `obj_2_Mold.stl`
- `obj_3_Sub-merged body.stl` → `obj_4_Push.stl`

Os contornos assimétricos das peças e das ferramentas coincidem por orientação: HAB-2 tem a região larga no mesmo extremo do Mold; Sub-merged body coincide com Push.

## O que o v0.1 calcula

1. Faz uma seção da peça plana em `z = 0,5 mm`.
2. Detecta automaticamente as 65 aberturas hexagonais.
3. Usa os centros das células para construir uma rede de vizinhança de passo ~8 mm.
4. Extrai a superfície superior real do STL da ferramenta como `z = f(x,y)`.
5. Calcula dois casos:
   - **projeção direta**: X/Y ficam travados e a rede é levada diretamente para `z=f(x,y)`;
   - **drape relaxado**: os centros podem migrar em X/Y sobre a ferramenta, enquanto a borda recebe ancoragem mais forte e a rede tenta preservar seus comprimentos originais.
6. Gera um primeiro candidato de preenchimento com mais reserva de material nas zonas de maior demanda.

## Interpretação correta dos números

`effective stretch` NÃO é ainda deformação verdadeira do PETG/PLA e NÃO é tensão de von Mises. É a variação de comprimento das arestas de uma rede geométrica equivalente de centros de células. O objetivo desta etapa é localizar incompatibilidade geométrica e estimar quanto fluxo de material no plano reduz o problema.

O caso de projeção direta funciona como um limite muito rígido e superestima fortemente a deformação nos ombros da ferramenta. O caso relaxado é mais representativo da capacidade da malha vazada de deslocar, girar e alimentar material durante a termoformagem, mas ainda não inclui rigidez real dos ligamentos, temperatura, atrito ou contato macho-fêmea.

## Resultados v0.1

### HAB-2 → Mold

- 65 células e 164 relações de vizinhança.
- Projeção direta: média de demanda efetiva ~18,0%; P95 ~60,9%; pico ~152,7%.
- Drape relaxado: média ~7,5%; P95 ~15,4%; pico ~21,2%.
- Fluxo lateral necessário: média ~1,19 mm; máximo ~2,47 mm.
- Primeiro candidato: lado dos hexágonos de aproximadamente 3,36 a 3,97 mm, contra 4,00 mm atuais, criando maior ligamento nas regiões críticas.

### Sub-merged body → Push

- 65 células e 164 relações de vizinhança.
- Projeção direta: média ~19,8%; P95 ~68,3%; pico ~165,5%.
- Drape relaxado: média ~8,0%; P95 ~15,1%; pico ~23,7%.
- Fluxo lateral necessário: média ~1,47 mm; máximo ~3,32 mm.
- Primeiro candidato: lado dos hexágonos de aproximadamente 3,34 a 4,00 mm.

A redução enorme entre projeção direta e drape relaxado mostra que alguns milímetros de movimento no plano têm impacto maior do que simplesmente engrossar toda a peça.

## Candidato v0.1

O candidato v0.1 é deliberadamente conservador e heurístico. Para cada célula, parte da demanda residual do drape relaxado é convertida em **reserva de material**: a abertura hexagonal diminui localmente e o ligamento aumenta. Ele NÃO deve ser tratado como geometria ótima final; serve como primeira peça experimental baseada no campo calculado.

Parâmetros principais estão no dicionário `CONFIG` do script:

- lado atual do hexágono: 4,0 mm;
- pitch: 8,0 mm;
- fator de compensação: 0,65;
- limite de lambda de projeto: 1,22;
- lado mínimo permitido: 2,8 mm.

## Arquivos de resultado

Para cada metade são gerados:

- `*_3d_drape.html`: visualização 3D interativa da ferramenta, projeção direta e drape relaxado;
- `*_relaxed_demand.png`: mapa 2D da demanda geométrica residual;
- `*_candidate_hex_size.png`: tamanho de célula sugerido pelo candidato v0.1;
- `*_original_vs_candidate.svg`: comparação vetorial do desenho plano atual com o candidato;
- `*_cells.csv`: métricas de cada uma das 65 células.

`summary.json` contém as métricas consolidadas.

## Executar

```bash
python lampform_lab_v01.py
```

Dependências utilizadas: `numpy`, `pandas`, `scipy`, `shapely`, `trimesh`, `matplotlib` e `plotly`.

## Próximo gate recomendado — v0.2

Substituir a rede de centros por uma **rede estrutural dos ligamentos reais**. A geometria pode ser reconstruída a partir da tesselação de Voronoi dos centros dos 65 vazios, gerando os eixos das paredes do honeycomb. Cada ligamento passa a ter comprimento, largura, altura e rigidez próprios.

O solver v0.2 deve incluir:

- grandes deslocamentos;
- energia axial e de flexão dos ligamentos;
- nós com rotação/compliance;
- contato com a superfície da ferramenta;
- rigidez da borda de 4 mm;
- variação espacial de largura do ligamento;
- comparação automática entre malha atual e candidatos.

Depois disso, a calibração física deve incorporar material, temperatura, tempo de aquecimento, direção das linhas de impressão e atrito. Só então faz sentido chamar o resultado de FEA termo-mecânico quantitativo.

---

# v0.2 — rede estrutural dos ligamentos

O script `lampform_ligament_v02.py` reconstrói uma rede de **173 nós e 234 ligamentos** a partir da geometria real das 65 células. Em vez de usar apenas os centros dos vazios, ele aproxima os eixos médios das paredes do honeycomb e resolve grandes deslocamentos sobre a superfície real do molde.

É um **beam-network surrogate**, ainda não um FEA constitutivo. O comprimento de cada ligamento é tratado como grau de liberdade estrutural e os nós recebem uma pequena penalização angular. A periferia pode ser mais ou menos ancorada para representar a rigidez do aro e a capacidade de alimentar material durante a conformação.

## Resultado principal da v0.2

Com uma borda relativamente rígida (`boundary_anchor = 2.0`):

- HAB-2 → Mold: demanda axial efetiva média ~20,3%, P95 ~32,8%, máximo ~53,2%.
- Sub-merged → Push: média ~20,8%, P95 ~34,6%, máximo ~51,7%.

Esses números são superiores aos da rede de centros da v0.1 porque agora a métrica é aplicada aos próprios eixos dos ligamentos, que atravessam regiões de gradiente geométrico elevado.

## Descoberta mais importante: sensibilidade ao aro

A varredura de `boundary_anchor` mostra que a capacidade de a periferia alimentar material é um dos parâmetros dominantes do problema.

Para Sub-merged → Push, por exemplo:

- ancoragem 5,0: máximo ~130%;
- 2,0: máximo ~51,7%;
- 0,5: máximo ~43,6%;
- 0,2: P95 ~18,4%;
- 0,05: P95 ~6,2% e máximo ~6,9%.

Isso NÃO significa que `0,05` seja um valor físico calibrado. Significa que, dentro deste modelo, liberar o fluxo da borda pode reduzir a demanda mais do que alterar apenas a flexibilidade angular dos nós.

A sensibilidade à penalização de flexão dos nós foi comparativamente pequena. Isso indica que **"fazer um hexágono mais articulado" sem resolver a restrição da periferia provavelmente não será suficiente**.

## Hipótese de projeto que emerge

A próxima geometria deve testar conjuntamente:

1. **reserva de material local**: reduzir a abertura dos hexágonos nas regiões críticas;
2. **zona de transição compliant entre lattice e aro**: slots, necks, ondas ou segmentos que permitam alguns milímetros de feed durante a termoformagem;
3. **aro final rígido somente depois da formação**, ou um aro com região sacrificial a ser cortada após o processo;
4. comparação contra a peça atual usando as mesmas métricas.

A v0.2 gera, para cada metade:

- `*_ligament_3d.html`: visualizador 3D da rede de ligamentos sobre a ferramenta;
- `*_ligaments.csv`: resultado por ligamento;
- `*_boundary_sensitivity.csv`: sweep da rigidez da periferia;
- `*_boundary_sensitivity.png`: gráfico da influência do aro;
- `summary_v02.json`: consolidação das métricas.

O passo seguinte é transformar a sensibilidade do aro em uma **geometria fabricável**, gerar um candidato STL/SVG e rodar novamente o solver para comparar baseline x candidato.
