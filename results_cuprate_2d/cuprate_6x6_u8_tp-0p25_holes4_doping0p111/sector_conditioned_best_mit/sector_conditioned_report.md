# 2D Cuprate Sector-Conditioned Hardware Comparison

This report reuses existing raw bitstring counts only. No IBM Runtime, Fire Opal, or hardware job was submitted.

Postselection is a diagnostic, not mitigation proof: if few shots survive, the resulting observables have high statistical noise.

## Sector Survival

| source | profile | kept shots | total shots | kept fraction | discard fraction | unique kept | mean abs dN_up | mean abs dN_down |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| ibm_best_mit | exact_sector | 0 | 1024 | 0.000000 | 1.000000 | 0 | 0.000000 | 0.000000 |
| ibm_best_mit | near_sector_l1_le_1 | 0 | 1024 | 0.000000 | 1.000000 | 0 | 0.000000 | 0.000000 |
| ibm_best_mit | near_sector_l1_le_2 | 0 | 1024 | 0.000000 | 1.000000 | 0 | 0.000000 | 0.000000 |
| fire_opal_best_mit | exact_sector | 10 | 1024 | 0.009766 | 0.990234 | 10 | 0.000000 | 0.000000 |
| fire_opal_best_mit | near_sector_l1_le_1 | 37 | 1024 | 0.036133 | 0.963867 | 37 | 0.405405 | 0.324324 |
| fire_opal_best_mit | near_sector_l1_le_2 | 112 | 1024 | 0.109375 | 0.890625 | 112 | 0.785714 | 0.794643 |

## Site Summaries

| source | profile | total charge | total spin-z | mean abs spin-z | mean doublon | min charge | max charge |
|---|---|---:|---:|---:|---:|---:|---:|
| fire_opal_best_mit | exact_sector | 32.000000 | -0.000000 | 0.155556 | 0.200000 | 0.600000 | 1.400000 |
| fire_opal_best_mit | near_sector_l1_le_1 | 32.243243 | 0.351351 | 0.077327 | 0.203453 | 0.675676 | 1.189189 |
| fire_opal_best_mit | near_sector_l1_le_2 | 32.491071 | 0.008929 | 0.057292 | 0.202133 | 0.776786 | 1.071429 |
| fire_opal_best_mit | unfiltered_raw | 36.298828 | -0.101562 | 0.030707 | 0.252170 | 0.904297 | 1.170898 |
| gaussian_u0 | free_fermion_step1 | 32.000000 | -0.000000 | 0.836350 | 0.025179 | 0.021613 | 1.000000 |
| ibm_best_mit | unfiltered_raw | 17.526367 | -0.547852 | 0.104791 | 0.084581 | 0.007812 | 1.027344 |
| tdhf | mean_field_step1 | 32.000000 | -0.000000 | 0.838992 | 0.023967 | 0.021113 | 1.000001 |

## RMSE vs TDHF Step 1

| source | profile | charge RMSE | spin-z RMSE | doublon RMSE | sites |
|---|---|---:|---:|---:|---:|
| fire_opal_best_mit | exact_sector | 0.320103 | 0.876957 | 0.211924 | 36 |
| fire_opal_best_mit | near_sector_l1_le_1 | 0.321362 | 0.863489 | 0.192282 | 36 |
| fire_opal_best_mit | near_sector_l1_le_2 | 0.316569 | 0.886607 | 0.182697 | 36 |
| fire_opal_best_mit | unfiltered_raw | 0.321863 | 0.889892 | 0.229493 | 36 |
| gaussian_u0 | free_fermion_step1 | 0.000195 | 0.002836 | 0.001297 | 36 |
| ibm_best_mit | unfiltered_raw | 0.626647 | 0.881339 | 0.105383 | 36 |

## Artifacts

- site observables: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/sector_conditioned_best_mit/sector_conditioned_site_observables.csv`
- observable summary: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/sector_conditioned_best_mit/sector_conditioned_observable_summary.csv`
- RMSE: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/sector_conditioned_best_mit/sector_conditioned_observable_rmse.csv`
- sector summary: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/sector_conditioned_best_mit/sector_conditioned_sector_summary.csv`
- metadata: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/sector_conditioned_best_mit/sector_conditioned_metadata.json`

Interpretation boundary: sector-conditioned rows are useful to diagnose whether the correct conserved sector contains a TDHF-like signal. They are not standalone physical evidence when survival is small.
