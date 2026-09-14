# Video storyboard — LampForm Lab v0.6

1920 × 1080; 12 cenas. ←/→ e Space navegam; Esc volta à bancada. Detalhes de cada cena têm controles próprios. URL: story.html?scene=06; captura limpa: story.html?scene=06&mode=capture.

## 01 — The object

Visual: Flat STL → Mold ghost

Main point: The lamp starts as a flat FDM lattice and is thermoformed into a doubly curved shell.

Suggested narration: Apresentar a peça original real. A falha na termoformação é o problema relatado pelo autor; ainda não há registro experimental no app.

Duration hint: 15 s; camera: isometric.

## 02 — The problem

Visual: Flat → Formed → High demand

Main point: A flat lattice cannot conform to this surface without stretching, rotating or feeding material.

Suggested narration: Mostrar a incompatibilidade geométrica; não chamar as cores de tensão PETG.

Duration hint: 15 s; camera: isometric.

## 03 — The mold

Visual: Mold / Push → Dimensions

Main point: The real mold geometry becomes the target surface, instead of an assumed hemisphere.

Suggested narration: As duas ferramentas vêm dos STL originais. Posições de apresentação não simulam contato entre ferramentas.

Duration hint: 15 s; camera: isometric.

## 04 — Digital reconstruction

Visual: Real STL → Detected cells → Nodes → Ligaments

Main point: Real STL → detected cells → nodes → ligaments.

Suggested narration: Explicar a correspondência entre 65 aberturas detectadas e a rede equivalente.

Duration hint: 15 s; camera: top.

## 05 — Forming

Visual: 0% → 25% → 50% → 75% → 100%

Main point: The solver searches for how the network can move in-plane while conforming to the mold.

Suggested narration: Cada etapa vem de uma solução real de continuação do solver.

Duration hint: 15 s; camera: isometric.

## 06 — Where does it want to deform?

Visual: λ1 → λ2 → Principal direction

Main point: The important question is not only how much deformation is required, but in which direction.

Suggested narration: Distinguir magnitudes e direções. Direções quase isotrópicas não são identificáveis.

Duration hint: 22 s; camera: top.

## 07 — The mechanisms

Visual: MATERIAL RESERVE → DIRECTIONAL COMPLIANCE → BOUNDARY FEED → AREA EXPANSION

Main point: Different regions may require different mechanisms.

Suggested narration: As categorias são hipóteses heurísticas, não mecanismos fisicamente provados.

Duration hint: 15 s; camera: top.

## 08 — Original design

Visual: Flat honeycomb → Risk map

Main point: Locate critical regions before changing the geometry.

Suggested narration: P95, máximo e contagem crítica vêm do mesmo modelo de referência.

Duration hint: 15 s; camera: top.

## 09 — Generative response

Visual: Overlay → Hole / ligament → Directional reserve → Boundary only

Main point: Test geometric reserve aligned with the estimated geometric mechanism.

Suggested narration: Mostrar exatamente onde há reserva e conectores curvos. Um conceito ondulado bidirecional não prova auxeticidade.

Duration hint: 15 s; camera: top.

## 10 — Does it improve?

Visual: Original | Candidate → Delta map

Main point: Improvement can move the problem: keep the same camera and color scale.

Suggested narration: Comparar melhora e piora. Sub-Merged permanece o problema mais difícil.

Duration hint: 15 s; camera: top.

## 11 — Simulation is not validation

Visual: Prediction → Print → Thermoform → Measure

Main point: A better simulation score does not prove a better physical part.

Suggested narration: Explicar por que obter um STL não encerra o trabalho.

Duration hint: 15 s; camera: isometric.

## 12 — Physical validation loop

Visual: A Original → B Reserve → C Boundary → D Hybrid → Predicted vs measured

Main point: MODEL → TEST → CALIBRATE → PREDICT

Suggested narration: Imprimir A/B/C/D, medir, calibrar no Original e validar em Candidate separado. Não existem medidas físicas ainda.

Duration hint: 15 s; camera: top.