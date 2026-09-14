# Parametric test V2 — hab2

A_uniform: width 1 mm, total lattice height 1 mm. This is the generated reference for this DOE, not a silent replacement of the supplied original STL.
B_width: width adaptive, height uniform. C_height: width uniform, height adaptive. D_both: both adaptive.
The same honeycomb graph, rim and anchor definition is retained. Height levels use 0.1 mm increments. Junction ends use the maximum neighboring height; steps are limited to 0.2 mm between adjacent parent ligaments.

The +10% budget is a cap relative to A lattice volume, excluding the unchanged rim. Quantization can leave unused budget; parameters and actual mesh volumes are included. B and C should be compared using their measured volume difference, not their names alone.

Print with 0.1 mm printer layer height and the same material, orientation and process. Inspect slicer layers before printing. Record material batch, heating distance/time, surface temperature and forming/holding/cooling times. No printer job is sent by LampForm.

Variable height changes both structural stiffness and thermal response. The current model evaluates the structural/geometric effect. Local heating differences are not yet calibrated. Out-of-plane section inertia is stored but full out-of-plane bending is not solved.

NO PHYSICAL VALIDATION DATA YET. These are experiments, not final recommended designs. The original files and v0.6 test pack remain available separately.
