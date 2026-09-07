# 2D Cuprate Observable Comparison

All sources are normalized to the same site variables: `n_up`, `n_down`, `charge`, `spin_z`, `hole_density`, and `double_occupancy`.

## Site Summaries

| source | profile | step | time | total charge | total spin-z | mean abs spin-z | mean doublon |
|---|---|---:|---:|---:|---:|---:|---:|
| exact_full | fixed_sector | 2 | 0.2 | 8.000000 | 0.000000 | 0.778109 | 0.049209 |
| exact_full | reference_step2 | 2 | 0.2 | 8.000000 | 0.000000 | 0.778109 | 0.049209 |
| exact_t_only | fixed_sector | 2 | 0.2 | 8.000000 | -0.000000 | 0.779968 | 0.048543 |
| fire_opal | exact_sector | 2 | 0.2 | 8.000000 | -0.000000 | 0.822094 | 0.026654 |
| fire_opal | near_sector_l1_le_1 | 2 | 0.2 | 8.039456 | -0.001361 | 0.767196 | 0.051550 |
| fire_opal | near_sector_l1_le_2 | 2 | 0.2 | 8.013742 | 0.075053 | 0.729269 | 0.060958 |
| fire_opal | raw | 2 | 0.2 | 8.041346 | 0.168269 | 0.703098 | 0.068910 |
| fire_opal | readout_corrected | 2 | 0.2 | 8.025377 | 0.184238 | 0.701324 | 0.068590 |
| fire_opal | unfiltered_raw | 2 | 0.2 | 8.041346 | 0.168269 | 0.703098 | 0.068910 |
| gaussian_u0 | free_fermion | 2 | 0.2 | 8.000000 | 0.000000 | 0.752594 | 0.060474 |
| gaussian_u0 | free_fermion_step2 | 2 | 0.2 | 8.000000 | 0.000000 | 0.752594 | 0.060474 |
| ibm | exact_sector | 2 | 0.2 | 8.000000 | 0.000000 | 0.578408 | 0.107959 |
| ibm | near_sector_l1_le_1 | 2 | 0.2 | 7.665953 | -0.025696 | 0.557221 | 0.098025 |
| ibm | near_sector_l1_le_2 | 2 | 0.2 | 7.450495 | 0.128713 | 0.530528 | 0.093234 |
| ibm | raw | 2 | 0.2 | 7.208984 | 0.234375 | 0.491536 | 0.090169 |
| ibm | readout_corrected | 2 | 0.2 | 7.247444 | 0.222842 | 0.502563 | 0.088789 |
| ibm | unfiltered_raw | 2 | 0.2 | 7.208984 | 0.234375 | 0.491536 | 0.090169 |
| tdhf | mean_field | 2 | 0.2 | 8.000000 | 0.000000 | 0.776874 | 0.050905 |
| tdhf | mean_field_step2 | 2 | 0.2 | 8.000000 | 0.000000 | 0.776874 | 0.050905 |

## RMSE

| source | profile | reference | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---|---|---:|---:|---:|
| exact_full | reference_step2 | exact_full:fixed_sector | 0.000000 | 0.000000 | 0.000000 |
| exact_t_only | fixed_sector | exact_full:fixed_sector | 0.001871 | 0.003245 | 0.000982 |
| fire_opal | exact_sector | exact_full:fixed_sector | 0.035551 | 0.074967 | 0.027467 |
| fire_opal | near_sector_l1_le_1 | exact_full:fixed_sector | 0.021429 | 0.058132 | 0.020591 |
| fire_opal | near_sector_l1_le_2 | exact_full:fixed_sector | 0.028397 | 0.084410 | 0.027154 |
| fire_opal | raw | exact_full:fixed_sector | 0.036987 | 0.104331 | 0.031956 |
| fire_opal | readout_corrected | exact_full:fixed_sector | 0.038743 | 0.106994 | 0.031627 |
| fire_opal | unfiltered_raw | exact_full:fixed_sector | 0.036987 | 0.104331 | 0.031956 |
| gaussian_u0 | free_fermion | exact_full:fixed_sector | 0.005167 | 0.026965 | 0.011859 |
| gaussian_u0 | free_fermion_step2 | exact_full:fixed_sector | 0.005167 | 0.026965 | 0.011859 |
| ibm | exact_sector | exact_full:fixed_sector | 0.123534 | 0.233135 | 0.073125 |
| ibm | near_sector_l1_le_1 | exact_full:fixed_sector | 0.141137 | 0.248568 | 0.055303 |
| ibm | near_sector_l1_le_2 | exact_full:fixed_sector | 0.162791 | 0.273283 | 0.049600 |
| ibm | raw | exact_full:fixed_sector | 0.185684 | 0.312551 | 0.046303 |
| ibm | readout_corrected | exact_full:fixed_sector | 0.188243 | 0.302231 | 0.046461 |
| ibm | unfiltered_raw | exact_full:fixed_sector | 0.185684 | 0.312551 | 0.046303 |
| tdhf | mean_field | exact_full:fixed_sector | 0.000196 | 0.001375 | 0.001822 |
| tdhf | mean_field_step2 | exact_full:fixed_sector | 0.000196 | 0.001375 | 0.001822 |

## Artifacts

- normalized site observables: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/observable_comparison_shallow_t_only_steps2_vs_exact_full/cuprate_2d_site_observables_normalized.csv`
- normalized bond observables: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/observable_comparison_shallow_t_only_steps2_vs_exact_full/cuprate_2d_bond_observables_normalized.csv`

Claim boundary: these are diagonal observables only. d-wave pairing still needs separate off-diagonal measurement circuits.
