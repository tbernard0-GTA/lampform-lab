# v0.8 implementation notes

Visual thesis: an off-white engineering documentary with a large, real lattice as the visual anchor; sage material, restrained typography, and color used only for quantitative fields.

Content plan: seven short chapters (Part, Problem, Digital model, Deformation, Redesign, Prediction, Physical test); the advanced controls live in /design, and earlier workbenches remain accessible.

Interaction thesis: a deliberate chapter crossfade, camera transitions between top/iso/side, and a slow sequence from uniform geometry to width/height adaptation using actual computed designs. Visual height exaggeration never changes downloads.

Computation strategy: bounded exact offline catalogue, all controls snap visibly to real generated/solved configurations. Variable height is quantized to 0.1 mm; beam section proxies distinguish area, in-plane inertia and out-of-plane inertia. Only XY node translations are independent solver degrees of freedom. No calibrated thermal or polymer failure predictions.

## Catalogue and interpretation

48 configurations, 24 per part. Uniform width/height combinations, three topologies, pitch and orientation examples, Reinforce/Comply and mechanism heuristics, and an equal-volume trio. Local adaptation is currently catalogued for Honeycomb only. Unsupported values snap visibly to an existing configuration within the selected topology. Controls always display the selected configuration. The static application retrieves its exact result; it does not run or interpolate the Python solver.

A_uniform is a generated reference with width and total lattice height 1 mm. Its original honeycomb graph and supplied rim are retained; it is not the supplied source STL. Source geometry remains available in the v0.6 workbench. The prior original deformation field guides the smoothed redesign, which is then solved again using the v0.8 section-aware surrogate. Cell IDs correspond only within the same topology and pitch.

Width and height affect axial section A=w·h and in-plane inertia I=h·w³/12. Out-of-plane inertia w·h³/12 is recorded, but independent out-of-plane bending is not solved. Angular penalties are relative geometric regularizers, not a calibrated beam finite-element model. Formed views show the solved network on the target surface; flat views and STL downloads show the actual manufactured solid.

The material budget excludes the unchanged rim. B/C/D target a +10% cap relative to A; height quantization can leave unused material. Width response 50% and 100% can reach the same capped solution. Equal-volume topology comparison uses the smallest common feasible range under width limits, about +38.22% vs A, rather than claiming a +10% solution exists for all topologies. All three have height 1 mm. Use actual volumes in the catalogue to compare.

Height means total lattice height. Parent edges have 0.1 mm quantization, neighboring height/width changes ≤0.2 mm, and 12 mm Gaussian smoothing. Junction end sections take the maximum neighboring height. The original rim is retained; its fillets are not quantized. Manifold union is simplified within 0.001 mm to remove serialization slivers, then the exported STL is reloaded and checked for watertightness, one body, finite coordinates, duplicate/degenerate faces, bounds and missing rim volume <0.01 mm.

## Verification

54 automated checks pass: 39 Node and 15 Python tests, including reload/hash checks for all 48 STLs, solver section properties, DOE factor isolation, neighboring feature bounds, fair-volume matching, exact catalogue selection and preserved v0.6 behavior.

Eight A/B/C/D STLs were sliced locally with installed CuraEngine 5.9.0 at 0.1 mm layer height: all returned success, 40 layers and no warnings/errors. This is a command-line check, not proof that every small feature survives the print process. The user chose to inspect the STL layers in Cura themselves. No printer job was submitted. Local G-code and printer settings are excluded from publication.

Permanent limitation: variable height changes structural stiffness and thermal response. Local heating differences, polymer behavior, contact and failure thresholds remain uncalibrated. No physical measurements were generated. The calculated P95 values should be compared within this v0.8 model, not directly with older solver versions.
