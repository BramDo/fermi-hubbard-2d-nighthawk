# 2D Cuprate Observable Comparison

All sources are normalized to the same site variables: `n_up`, `n_down`, `charge`, `spin_z`, `hole_density`, and `double_occupancy`.

## Site Summaries

| source | profile | step | time | total charge | total spin-z | mean abs spin-z | mean doublon |
|---|---|---:|---:|---:|---:|---:|---:|
| exact_full | fixed_sector | 3 | 0.3 | 8.000000 | -0.000000 | 0.707763 | 0.069466 |
| exact_full | reference_step3 | 3 | 0.3 | 8.000000 | -0.000000 | 0.707763 | 0.069466 |
| exact_t_only | fixed_sector | 3 | 0.3 | 8.000000 | 0.000000 | 0.711005 | 0.067535 |
| fire_opal | exact_sector | 3 | 0.3 | 8.000000 | -0.000000 | 0.737778 | 0.052840 |
| fire_opal | near_sector_l1_le_1 | 3 | 0.3 | 8.086039 | -0.095779 | 0.676587 | 0.079545 |
| fire_opal | near_sector_l1_le_2 | 3 | 0.3 | 8.180477 | -0.169126 | 0.636776 | 0.097112 |
| fire_opal | raw | 3 | 0.3 | 8.310511 | -0.152363 | 0.600236 | 0.112290 |
| fire_opal | readout_corrected | 3 | 0.3 | 8.300235 | -0.141238 | 0.599456 | 0.111695 |
| fire_opal | unfiltered_raw | 3 | 0.3 | 8.310511 | -0.152363 | 0.600236 | 0.112290 |
| gaussian_u0 | free_fermion | 3 | 0.3 | 8.000000 | -0.000000 | 0.603497 | 0.112242 |
| gaussian_u0 | free_fermion_step3 | 3 | 0.3 | 8.000000 | -0.000000 | 0.603497 | 0.112242 |
| ibm | exact_sector | 3 | 0.3 | 8.000000 | 0.000000 | 0.548148 | 0.098519 |
| ibm | near_sector_l1_le_1 | 3 | 0.3 | 7.789256 | 0.074380 | 0.516070 | 0.104683 |
| ibm | near_sector_l1_le_2 | 3 | 0.3 | 7.613065 | 0.115578 | 0.489391 | 0.104830 |
| ibm | raw | 3 | 0.3 | 7.503906 | 0.302734 | 0.452908 | 0.107205 |
| ibm | readout_corrected | 3 | 0.3 | 7.516324 | 0.356244 | 0.459429 | 0.104728 |
| ibm | unfiltered_raw | 3 | 0.3 | 7.503906 | 0.302734 | 0.452908 | 0.107205 |
| tdhf | mean_field | 3 | 0.3 | 8.000000 | 0.000000 | 0.699948 | 0.080622 |
| tdhf | mean_field_step3 | 3 | 0.3 | 8.000000 | 0.000000 | 0.699948 | 0.080622 |

## RMSE

| source | profile | reference | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---|---|---:|---:|---:|
| exact_full | reference_step3 | exact_full:fixed_sector | 0.000000 | 0.000000 | 0.000000 |
| exact_t_only | fixed_sector | exact_full:fixed_sector | 0.013111 | 0.006454 | 0.003472 |
| fire_opal | exact_sector | exact_full:fixed_sector | 0.031717 | 0.074023 | 0.023461 |
| fire_opal | near_sector_l1_le_1 | exact_full:fixed_sector | 0.037901 | 0.089729 | 0.035380 |
| fire_opal | near_sector_l1_le_2 | exact_full:fixed_sector | 0.046996 | 0.115021 | 0.048165 |
| fire_opal | raw | exact_full:fixed_sector | 0.063023 | 0.143104 | 0.060303 |
| fire_opal | readout_corrected | exact_full:fixed_sector | 0.060735 | 0.144364 | 0.059587 |
| fire_opal | unfiltered_raw | exact_full:fixed_sector | 0.063023 | 0.143104 | 0.060303 |
| gaussian_u0 | free_fermion | exact_full:fixed_sector | 0.019970 | 0.109488 | 0.044513 |
| gaussian_u0 | free_fermion_step3 | exact_full:fixed_sector | 0.019970 | 0.109488 | 0.044513 |
| ibm | exact_sector | exact_full:fixed_sector | 0.079577 | 0.182239 | 0.036406 |
| ibm | near_sector_l1_le_1 | exact_full:fixed_sector | 0.111627 | 0.228181 | 0.040179 |
| ibm | near_sector_l1_le_2 | exact_full:fixed_sector | 0.116673 | 0.252573 | 0.037368 |
| ibm | raw | exact_full:fixed_sector | 0.125039 | 0.284272 | 0.039896 |
| ibm | readout_corrected | exact_full:fixed_sector | 0.122483 | 0.281730 | 0.037212 |
| ibm | unfiltered_raw | exact_full:fixed_sector | 0.125039 | 0.284272 | 0.039896 |
| tdhf | mean_field | exact_full:fixed_sector | 0.001202 | 0.008724 | 0.011952 |
| tdhf | mean_field_step3 | exact_full:fixed_sector | 0.001202 | 0.008724 | 0.011952 |

## Artifacts

- normalized site observables: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/observable_comparison_shallow_t_only_steps3_vs_exact_full/cuprate_2d_site_observables_normalized.csv`
- normalized bond observables: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/observable_comparison_shallow_t_only_steps3_vs_exact_full/cuprate_2d_bond_observables_normalized.csv`

Claim boundary: these are diagonal observables only. d-wave pairing still needs separate off-diagonal measurement circuits.
