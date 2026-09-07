# 2D Cuprate Sector-Conditioned Hardware Comparison

This report reuses existing raw bitstring counts only. No IBM Runtime, Fire Opal, or hardware job was submitted.

Postselection is a diagnostic, not mitigation proof: if few shots survive, the resulting observables have high statistical noise.

## Sector Survival

| source | profile | kept shots | total shots | kept fraction | discard fraction | unique kept | mean abs dN_up | mean abs dN_down |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| ibm | exact_sector | 230 | 1024 | 0.224609 | 0.775391 | 54 | 0.000000 | 0.000000 |
| ibm | near_sector_l1_le_1 | 651 | 1024 | 0.635742 | 0.364258 | 211 | 0.188940 | 0.457757 |
| ibm | near_sector_l1_le_2 | 918 | 1024 | 0.896484 | 0.103516 | 362 | 0.346405 | 0.693900 |
| fire_opal | exact_sector | 588 | 1036 | 0.567568 | 0.432432 | 28 | 0.000000 | 0.000000 |
| fire_opal | near_sector_l1_le_1 | 851 | 1036 | 0.821429 | 0.178571 | 106 | 0.148061 | 0.160987 |
| fire_opal | near_sector_l1_le_2 | 982 | 1036 | 0.947876 | 0.052124 | 192 | 0.270876 | 0.263747 |

## Site Summaries

| source | profile | total charge | total spin-z | mean abs spin-z | mean doublon | min charge | max charge |
|---|---|---:|---:|---:|---:|---:|---:|
| fire_opal | exact_sector | 8.000000 | -0.000000 | 0.867725 | 0.009826 | 0.032313 | 1.015306 |
| fire_opal | near_sector_l1_le_1 | 8.003525 | 0.024677 | 0.824259 | 0.026635 | 0.084606 | 1.025852 |
| fire_opal | near_sector_l1_le_2 | 8.017312 | 0.039715 | 0.800973 | 0.033944 | 0.120163 | 1.028513 |
| fire_opal | unfiltered_raw | 8.060811 | 0.072394 | 0.784106 | 0.040755 | 0.151544 | 1.035714 |
| gaussian_u0 | free_fermion_step1 | 8.000000 | 0.000000 | 0.853300 | 0.017061 | 0.041738 | 0.999302 |
| ibm | exact_sector | 8.000000 | -0.000000 | 0.781643 | 0.046377 | 0.156522 | 1.069565 |
| ibm | near_sector_l1_le_1 | 7.746544 | 0.238095 | 0.717699 | 0.056836 | 0.181260 | 1.072197 |
| ibm | near_sector_l1_le_2 | 7.584967 | 0.375817 | 0.678891 | 0.060397 | 0.194989 | 1.064270 |
| ibm | unfiltered_raw | 7.536133 | 0.493164 | 0.655273 | 0.063260 | 0.222656 | 1.067383 |
| tdhf | mean_field_step1 | 8.000000 | 0.000000 | 0.855090 | 0.016260 | 0.040736 | 0.999552 |

## RMSE vs tdhf Step 1

| source | profile | charge RMSE | spin-z RMSE | doublon RMSE | sites |
|---|---|---:|---:|---:|---:|
| fire_opal | exact_sector | 0.012652 | 0.019317 | 0.010300 | 9 |
| fire_opal | near_sector_l1_le_1 | 0.027273 | 0.033757 | 0.017535 | 9 |
| fire_opal | near_sector_l1_le_2 | 0.035328 | 0.057683 | 0.023442 | 9 |
| fire_opal | unfiltered_raw | 0.043999 | 0.075021 | 0.029251 | 9 |
| gaussian_u0 | free_fermion_step1 | 0.000373 | 0.001896 | 0.000849 | 9 |
| ibm | exact_sector | 0.072167 | 0.098771 | 0.038580 | 9 |
| ibm | near_sector_l1_le_1 | 0.112684 | 0.170403 | 0.050364 | 9 |
| ibm | near_sector_l1_le_2 | 0.130596 | 0.212619 | 0.051629 | 9 |
| ibm | unfiltered_raw | 0.141055 | 0.235667 | 0.053688 | 9 |

## Artifacts

- site observables: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/sector_conditioned_shallow_t_only/sector_conditioned_site_observables.csv`
- observable summary: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/sector_conditioned_shallow_t_only/sector_conditioned_observable_summary.csv`
- RMSE: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/sector_conditioned_shallow_t_only/sector_conditioned_observable_rmse.csv`
- sector summary: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/sector_conditioned_shallow_t_only/sector_conditioned_sector_summary.csv`
- metadata: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/sector_conditioned_shallow_t_only/sector_conditioned_metadata.json`

Interpretation boundary: sector-conditioned rows are useful to diagnose whether the correct conserved sector contains a TDHF-like signal. They are not standalone physical evidence when survival is small.
