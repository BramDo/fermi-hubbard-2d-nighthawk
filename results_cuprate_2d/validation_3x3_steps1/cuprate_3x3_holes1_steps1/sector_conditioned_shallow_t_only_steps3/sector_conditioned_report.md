# 2D Cuprate Sector-Conditioned Hardware Comparison

This report reuses existing raw bitstring counts only. No IBM Runtime, Fire Opal, or hardware job was submitted.

Postselection is a diagnostic, not mitigation proof: if few shots survive, the resulting observables have high statistical noise.

## Sector Survival

| source | profile | kept shots | total shots | kept fraction | discard fraction | unique kept | mean abs dN_up | mean abs dN_down |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| ibm | exact_sector | 150 | 1024 | 0.146484 | 0.853516 | 101 | 0.000000 | 0.000000 |
| ibm | near_sector_l1_le_1 | 484 | 1024 | 0.472656 | 0.527344 | 355 | 0.353306 | 0.336777 |
| ibm | near_sector_l1_le_2 | 796 | 1024 | 0.777344 | 0.222656 | 616 | 0.590452 | 0.613065 |
| fire_opal | exact_sector | 225 | 1037 | 0.216972 | 0.783028 | 79 | 0.000000 | 0.000000 |
| fire_opal | near_sector_l1_le_1 | 616 | 1037 | 0.594021 | 0.405979 | 285 | 0.274351 | 0.360390 |
| fire_opal | near_sector_l1_le_2 | 881 | 1037 | 0.849566 | 0.150434 | 474 | 0.480136 | 0.565267 |

## Site Summaries

| source | profile | total charge | total spin-z | mean abs spin-z | mean doublon | min charge | max charge |
|---|---|---:|---:|---:|---:|---:|---:|
| exact_full | reference_step3 | 8.000000 | -0.000000 | 0.707763 | 0.069466 | 0.271265 | 1.002415 |
| fire_opal | exact_sector | 8.000000 | -0.000000 | 0.737778 | 0.052840 | 0.248889 | 1.053333 |
| fire_opal | near_sector_l1_le_1 | 8.086039 | -0.095779 | 0.676587 | 0.079545 | 0.301948 | 1.053571 |
| fire_opal | near_sector_l1_le_2 | 8.180477 | -0.169126 | 0.636776 | 0.097112 | 0.320091 | 1.063564 |
| fire_opal | unfiltered_raw | 8.310511 | -0.152363 | 0.600236 | 0.112290 | 0.373192 | 1.072324 |
| gaussian_u0 | free_fermion_step3 | 8.000000 | -0.000000 | 0.603497 | 0.112242 | 0.324960 | 0.989130 |
| ibm | exact_sector | 8.000000 | 0.000000 | 0.548148 | 0.098519 | 0.446667 | 1.013333 |
| ibm | near_sector_l1_le_1 | 7.789256 | 0.074380 | 0.516070 | 0.104683 | 0.471074 | 1.061983 |
| ibm | near_sector_l1_le_2 | 7.613065 | 0.115578 | 0.489391 | 0.104830 | 0.458543 | 1.012563 |
| ibm | unfiltered_raw | 7.503906 | 0.302734 | 0.452908 | 0.107205 | 0.466797 | 0.999023 |
| tdhf | mean_field_step3 | 8.000000 | 0.000000 | 0.699948 | 0.080622 | 0.274565 | 1.002311 |

## RMSE vs exact_full Step 3

| source | profile | charge RMSE | spin-z RMSE | doublon RMSE | sites |
|---|---|---:|---:|---:|---:|
| fire_opal | exact_sector | 0.031717 | 0.074023 | 0.023461 | 9 |
| fire_opal | near_sector_l1_le_1 | 0.037901 | 0.089729 | 0.035380 | 9 |
| fire_opal | near_sector_l1_le_2 | 0.046996 | 0.115021 | 0.048165 | 9 |
| fire_opal | unfiltered_raw | 0.063023 | 0.143104 | 0.060303 | 9 |
| gaussian_u0 | free_fermion_step3 | 0.019970 | 0.109488 | 0.044513 | 9 |
| ibm | exact_sector | 0.079577 | 0.182239 | 0.036406 | 9 |
| ibm | near_sector_l1_le_1 | 0.111627 | 0.228181 | 0.040179 | 9 |
| ibm | near_sector_l1_le_2 | 0.116673 | 0.252573 | 0.037368 | 9 |
| ibm | unfiltered_raw | 0.125039 | 0.284272 | 0.039896 | 9 |
| tdhf | mean_field_step3 | 0.001202 | 0.008724 | 0.011952 | 9 |

## Artifacts

- site observables: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/sector_conditioned_shallow_t_only_steps3/sector_conditioned_site_observables.csv`
- observable summary: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/sector_conditioned_shallow_t_only_steps3/sector_conditioned_observable_summary.csv`
- RMSE: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/sector_conditioned_shallow_t_only_steps3/sector_conditioned_observable_rmse.csv`
- sector summary: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/sector_conditioned_shallow_t_only_steps3/sector_conditioned_sector_summary.csv`
- metadata: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/sector_conditioned_shallow_t_only_steps3/sector_conditioned_metadata.json`

Interpretation boundary: sector-conditioned rows are useful to diagnose whether the correct conserved sector contains a TDHF-like signal. They are not standalone physical evidence when survival is small.
