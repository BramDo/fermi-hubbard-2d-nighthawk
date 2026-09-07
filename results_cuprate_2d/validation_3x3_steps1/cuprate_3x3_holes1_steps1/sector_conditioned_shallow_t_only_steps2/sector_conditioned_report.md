# 2D Cuprate Sector-Conditioned Hardware Comparison

This report reuses existing raw bitstring counts only. No IBM Runtime, Fire Opal, or hardware job was submitted.

Postselection is a diagnostic, not mitigation proof: if few shots survive, the resulting observables have high statistical noise.

## Sector Survival

| source | profile | kept shots | total shots | kept fraction | discard fraction | unique kept | mean abs dN_up | mean abs dN_down |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| ibm | exact_sector | 141 | 1024 | 0.137695 | 0.862305 | 94 | 0.000000 | 0.000000 |
| ibm | near_sector_l1_le_1 | 467 | 1024 | 0.456055 | 0.543945 | 320 | 0.359743 | 0.338330 |
| ibm | near_sector_l1_le_2 | 808 | 1024 | 0.789062 | 0.210938 | 585 | 0.618812 | 0.628713 |
| fire_opal | exact_sector | 346 | 1040 | 0.332692 | 0.667308 | 50 | 0.000000 | 0.000000 |
| fire_opal | near_sector_l1_le_1 | 735 | 1040 | 0.706731 | 0.293269 | 175 | 0.209524 | 0.319728 |
| fire_opal | near_sector_l1_le_2 | 946 | 1040 | 0.909615 | 0.090385 | 317 | 0.378436 | 0.478858 |

## Site Summaries

| source | profile | total charge | total spin-z | mean abs spin-z | mean doublon | min charge | max charge |
|---|---|---:|---:|---:|---:|---:|---:|
| exact_full | reference_step2 | 8.000000 | 0.000000 | 0.778109 | 0.049209 | 0.144241 | 0.999824 |
| fire_opal | exact_sector | 8.000000 | -0.000000 | 0.822094 | 0.026654 | 0.080925 | 1.011561 |
| fire_opal | near_sector_l1_le_1 | 8.039456 | -0.001361 | 0.767196 | 0.051550 | 0.126531 | 1.034014 |
| fire_opal | near_sector_l1_le_2 | 8.013742 | 0.075053 | 0.729269 | 0.060958 | 0.178647 | 1.030655 |
| fire_opal | unfiltered_raw | 8.041346 | 0.168269 | 0.703098 | 0.068910 | 0.215385 | 1.023077 |
| gaussian_u0 | free_fermion_step2 | 8.000000 | 0.000000 | 0.752594 | 0.060474 | 0.158126 | 0.996380 |
| ibm | exact_sector | 8.000000 | 0.000000 | 0.578408 | 0.107959 | 0.390071 | 1.092199 |
| ibm | near_sector_l1_le_1 | 7.665953 | -0.025696 | 0.557221 | 0.098025 | 0.391863 | 1.019272 |
| ibm | near_sector_l1_le_2 | 7.450495 | 0.128713 | 0.530528 | 0.093234 | 0.417079 | 1.009901 |
| ibm | unfiltered_raw | 7.208984 | 0.234375 | 0.491536 | 0.090169 | 0.429688 | 0.981445 |
| tdhf | mean_field_step2 | 8.000000 | 0.000000 | 0.776874 | 0.050905 | 0.144794 | 0.999747 |

## RMSE vs exact_full Step 2

| source | profile | charge RMSE | spin-z RMSE | doublon RMSE | sites |
|---|---|---:|---:|---:|---:|
| fire_opal | exact_sector | 0.035551 | 0.074967 | 0.027467 | 9 |
| fire_opal | near_sector_l1_le_1 | 0.021429 | 0.058132 | 0.020591 | 9 |
| fire_opal | near_sector_l1_le_2 | 0.028397 | 0.084410 | 0.027154 | 9 |
| fire_opal | unfiltered_raw | 0.036987 | 0.104331 | 0.031956 | 9 |
| gaussian_u0 | free_fermion_step2 | 0.005167 | 0.026965 | 0.011859 | 9 |
| ibm | exact_sector | 0.123534 | 0.233135 | 0.073125 | 9 |
| ibm | near_sector_l1_le_1 | 0.141137 | 0.248568 | 0.055303 | 9 |
| ibm | near_sector_l1_le_2 | 0.162791 | 0.273283 | 0.049600 | 9 |
| ibm | unfiltered_raw | 0.185684 | 0.312551 | 0.046303 | 9 |
| tdhf | mean_field_step2 | 0.000196 | 0.001375 | 0.001822 | 9 |

## Artifacts

- site observables: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/sector_conditioned_shallow_t_only_steps2/sector_conditioned_site_observables.csv`
- observable summary: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/sector_conditioned_shallow_t_only_steps2/sector_conditioned_observable_summary.csv`
- RMSE: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/sector_conditioned_shallow_t_only_steps2/sector_conditioned_observable_rmse.csv`
- sector summary: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/sector_conditioned_shallow_t_only_steps2/sector_conditioned_sector_summary.csv`
- metadata: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/sector_conditioned_shallow_t_only_steps2/sector_conditioned_metadata.json`

Interpretation boundary: sector-conditioned rows are useful to diagnose whether the correct conserved sector contains a TDHF-like signal. They are not standalone physical evidence when survival is small.
