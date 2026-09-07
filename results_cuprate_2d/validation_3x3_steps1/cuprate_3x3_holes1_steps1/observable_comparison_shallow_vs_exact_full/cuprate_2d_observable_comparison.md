# 2D Cuprate Observable Comparison

All sources are normalized to the same site variables: `n_up`, `n_down`, `charge`, `spin_z`, `hole_density`, and `double_occupancy`.

## Site Summaries

| source | profile | step | time | total charge | total spin-z | mean abs spin-z | mean doublon |
|---|---|---:|---:|---:|---:|---:|---:|
| exact_full | fixed_sector | 1 | 0.1 | 8.000000 | 0.000000 | 0.855116 | 0.016223 |
| exact_t_only | fixed_sector | 1 | 0.1 | 8.000000 | 0.000000 | 0.855648 | 0.016165 |
| fire_opal | raw |  |  | 8.060811 | 0.072394 | 0.784106 | 0.040755 |
| fire_opal | readout_corrected |  |  | 8.050515 | 0.081528 | 0.784235 | 0.040020 |
| gaussian_u0 | free_fermion | 1 | 0.1 | 8.000000 | 0.000000 | 0.853300 | 0.017061 |
| ibm | raw |  |  | 7.536133 | 0.493164 | 0.655273 | 0.063260 |
| ibm | readout_corrected |  |  | 7.564247 | 0.518122 | 0.673231 | 0.057248 |
| tdhf | mean_field | 1 | 0.1 | 8.000000 | 0.000000 | 0.855090 | 0.016260 |

## RMSE

| source | profile | reference | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---|---|---:|---:|---:|
| exact_t_only | fixed_sector | exact_full:fixed_sector | 0.000519 | 0.000896 | 0.000079 |
| fire_opal | raw | exact_full:fixed_sector | 0.044003 | 0.075049 | 0.029284 |
| fire_opal | readout_corrected | exact_full:fixed_sector | 0.044332 | 0.075335 | 0.028962 |
| gaussian_u0 | free_fermion | exact_full:fixed_sector | 0.000378 | 0.001924 | 0.000889 |
| ibm | raw | exact_full:fixed_sector | 0.141058 | 0.235693 | 0.053722 |
| ibm | readout_corrected | exact_full:fixed_sector | 0.137934 | 0.221699 | 0.045795 |
| tdhf | mean_field | exact_full:fixed_sector | 0.000004 | 0.000029 | 0.000040 |

## Artifacts

- normalized site observables: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/observable_comparison_shallow_vs_exact_full/cuprate_2d_site_observables_normalized.csv`
- normalized bond observables: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/observable_comparison_shallow_vs_exact_full/cuprate_2d_bond_observables_normalized.csv`

Claim boundary: these are diagonal observables only. d-wave pairing still needs separate off-diagonal measurement circuits.
