# 2D Cuprate Observable Comparison

All sources are normalized to the same site variables: `n_up`, `n_down`, `charge`, `spin_z`, `hole_density`, and `double_occupancy`.

## Site Summaries

| source | profile | step | time | total charge | total spin-z | mean abs spin-z | mean doublon |
|---|---|---:|---:|---:|---:|---:|---:|
| exact_full | fixed_sector | 1 | 0.1 | 8.000000 | 0.000000 | 0.855116 | 0.016223 |
| exact_t_only | fixed_sector | 1 | 0.1 | 8.000000 | 0.000000 | 0.855648 | 0.016165 |
| fire_opal | exact_sector |  |  | 8.000000 | -0.000000 | 0.867725 | 0.009826 |
| fire_opal | near_sector_l1_le_1 |  |  | 8.003525 | 0.024677 | 0.824259 | 0.026635 |
| fire_opal | near_sector_l1_le_2 |  |  | 8.017312 | 0.039715 | 0.800973 | 0.033944 |
| fire_opal | unfiltered_raw |  |  | 8.060811 | 0.072394 | 0.784106 | 0.040755 |
| gaussian_u0 | free_fermion_step1 | 1 | 0.1 | 8.000000 | 0.000000 | 0.853300 | 0.017061 |
| ibm | exact_sector |  |  | 8.000000 | -0.000000 | 0.781643 | 0.046377 |
| ibm | near_sector_l1_le_1 |  |  | 7.746544 | 0.238095 | 0.717699 | 0.056836 |
| ibm | near_sector_l1_le_2 |  |  | 7.584967 | 0.375817 | 0.678891 | 0.060397 |
| ibm | unfiltered_raw |  |  | 7.536133 | 0.493164 | 0.655273 | 0.063260 |
| tdhf | mean_field_step1 | 1 | 0.1 | 8.000000 | 0.000000 | 0.855090 | 0.016260 |

## RMSE

| source | profile | reference | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---|---|---:|---:|---:|
| exact_t_only | fixed_sector | exact_full:fixed_sector | 0.000519 | 0.000896 | 0.000079 |
| fire_opal | exact_sector | exact_full:fixed_sector | 0.012651 | 0.019293 | 0.010273 |
| fire_opal | near_sector_l1_le_1 | exact_full:fixed_sector | 0.027275 | 0.033783 | 0.017559 |
| fire_opal | near_sector_l1_le_2 | exact_full:fixed_sector | 0.035331 | 0.057711 | 0.023473 |
| fire_opal | unfiltered_raw | exact_full:fixed_sector | 0.044003 | 0.075049 | 0.029284 |
| gaussian_u0 | free_fermion_step1 | exact_full:fixed_sector | 0.000378 | 0.001924 | 0.000889 |
| ibm | exact_sector | exact_full:fixed_sector | 0.072170 | 0.098797 | 0.038610 |
| ibm | near_sector_l1_le_1 | exact_full:fixed_sector | 0.112686 | 0.170429 | 0.050396 |
| ibm | near_sector_l1_le_2 | exact_full:fixed_sector | 0.130598 | 0.212645 | 0.051663 |
| ibm | unfiltered_raw | exact_full:fixed_sector | 0.141058 | 0.235693 | 0.053722 |
| tdhf | mean_field_step1 | exact_full:fixed_sector | 0.000004 | 0.000029 | 0.000040 |

## Artifacts

- normalized site observables: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/observable_comparison_shallow_sector_vs_exact_full/cuprate_2d_site_observables_normalized.csv`

Claim boundary: these are diagonal observables only. d-wave pairing still needs separate off-diagonal measurement circuits.
