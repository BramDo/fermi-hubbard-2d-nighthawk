# 2D Cuprate Sector-Conditioned Hardware Comparison

This report reuses existing raw bitstring counts only. No IBM Runtime, Fire Opal, or hardware job was submitted.

Postselection is a diagnostic, not mitigation proof: if few shots survive, the resulting observables have high statistical noise.

## Sector Survival

| source | profile | kept shots | total shots | kept fraction | discard fraction | unique kept | mean abs dN_up | mean abs dN_down |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| ibm | exact_sector | 133 | 1024 | 0.129883 | 0.870117 | 83 | 0.000000 | 0.000000 |
| ibm | near_sector_l1_le_1 | 462 | 1024 | 0.451172 | 0.548828 | 339 | 0.329004 | 0.383117 |
| ibm | near_sector_l1_le_2 | 762 | 1024 | 0.744141 | 0.255859 | 607 | 0.556430 | 0.662730 |
| fire_opal | exact_sector | 267 | 1053 | 0.253561 | 0.746439 | 62 | 0.000000 | 0.000000 |
| fire_opal | near_sector_l1_le_1 | 654 | 1053 | 0.621083 | 0.378917 | 260 | 0.316514 | 0.275229 |
| fire_opal | near_sector_l1_le_2 | 895 | 1053 | 0.849953 | 0.150047 | 469 | 0.505028 | 0.465922 |

## Site Summaries

| source | profile | total charge | total spin-z | mean abs spin-z | mean doublon | min charge | max charge |
|---|---|---:|---:|---:|---:|---:|---:|
| fire_opal | exact_sector | 14.000000 | -0.000000 | 0.827715 | 0.019195 | 0.029963 | 1.033708 |
| fire_opal | near_sector_l1_le_1 | 14.099388 | -0.041284 | 0.788895 | 0.038322 | 0.094801 | 1.055046 |
| fire_opal | near_sector_l1_le_2 | 14.182123 | -0.056983 | 0.770042 | 0.047905 | 0.127374 | 1.072626 |
| fire_opal | unfiltered_raw | 14.268756 | -0.061728 | 0.753977 | 0.055318 | 0.150997 | 1.070275 |
| gaussian_u0 | free_fermion_step1 | 14.000000 | 0.000000 | 0.832662 | 0.020219 | 0.032018 | 0.999993 |
| ibm | exact_sector | 14.000000 | 0.000000 | 0.739662 | 0.048402 | 0.172932 | 1.082707 |
| ibm | near_sector_l1_le_1 | 13.824675 | -0.101732 | 0.693588 | 0.060471 | 0.220779 | 1.069264 |
| ibm | near_sector_l1_le_2 | 13.704724 | -0.177165 | 0.676263 | 0.063402 | 0.220472 | 1.039370 |
| ibm | unfiltered_raw | 13.766602 | -0.340820 | 0.650818 | 0.072632 | 0.253906 | 1.037109 |
| mps | reference_step1 | 14.000000 | 0.000000 | 0.833332 | 0.020170 | 0.029590 | 1.000008 |
| tdhf | mean_field_step1 | 14.000000 | 0.000000 | 0.834784 | 0.019260 | 0.031266 | 0.999995 |

## RMSE vs mps Step 1

| source | profile | charge RMSE | spin-z RMSE | doublon RMSE | sites |
|---|---|---:|---:|---:|---:|
| fire_opal | exact_sector | 0.026794 | 0.021459 | 0.013010 | 16 |
| fire_opal | near_sector_l1_le_1 | 0.050037 | 0.064129 | 0.026250 | 16 |
| fire_opal | near_sector_l1_le_2 | 0.056713 | 0.087133 | 0.037373 | 16 |
| fire_opal | unfiltered_raw | 0.065163 | 0.104742 | 0.045752 | 16 |
| gaussian_u0 | free_fermion_step1 | 0.000955 | 0.000917 | 0.000088 | 16 |
| ibm | exact_sector | 0.097011 | 0.123450 | 0.044959 | 16 |
| ibm | near_sector_l1_le_1 | 0.101181 | 0.167410 | 0.047666 | 16 |
| ibm | near_sector_l1_le_2 | 0.111747 | 0.189604 | 0.050894 | 16 |
| ibm | unfiltered_raw | 0.119908 | 0.218926 | 0.059685 | 16 |
| tdhf | mean_field_step1 | 0.000660 | 0.002011 | 0.000995 | 16 |

## Artifacts

- site observables: `results_cuprate_2d/validation_ladder_steps1/cuprate_4x4_holes2_steps1/sector_conditioned_fire_opal_qelib_retry_steps1_vs_mps/sector_conditioned_site_observables.csv`
- observable summary: `results_cuprate_2d/validation_ladder_steps1/cuprate_4x4_holes2_steps1/sector_conditioned_fire_opal_qelib_retry_steps1_vs_mps/sector_conditioned_observable_summary.csv`
- RMSE: `results_cuprate_2d/validation_ladder_steps1/cuprate_4x4_holes2_steps1/sector_conditioned_fire_opal_qelib_retry_steps1_vs_mps/sector_conditioned_observable_rmse.csv`
- sector summary: `results_cuprate_2d/validation_ladder_steps1/cuprate_4x4_holes2_steps1/sector_conditioned_fire_opal_qelib_retry_steps1_vs_mps/sector_conditioned_sector_summary.csv`
- metadata: `results_cuprate_2d/validation_ladder_steps1/cuprate_4x4_holes2_steps1/sector_conditioned_fire_opal_qelib_retry_steps1_vs_mps/sector_conditioned_metadata.json`

Interpretation boundary: sector-conditioned rows are useful to diagnose whether the correct conserved sector contains a TDHF-like signal. They are not standalone physical evidence when survival is small.
