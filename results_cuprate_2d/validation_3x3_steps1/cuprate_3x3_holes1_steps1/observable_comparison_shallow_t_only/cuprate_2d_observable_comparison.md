# 2D Cuprate Observable Comparison

All sources are normalized to the same site variables: `n_up`, `n_down`, `charge`, `spin_z`, `hole_density`, and `double_occupancy`.

## Site Summaries

| source | profile | step | time | total charge | total spin-z | mean abs spin-z | mean doublon |
|---|---|---:|---:|---:|---:|---:|---:|
| fire_opal | raw |  |  | 8.060811 | 0.072394 | 0.784106 | 0.040755 |
| fire_opal | readout_corrected |  |  | 8.050515 | 0.081528 | 0.784235 | 0.040020 |
| gaussian_u0 | free_fermion | 1 | 0.1 | 8.000000 | 0.000000 | 0.853300 | 0.017061 |
| ibm | raw |  |  | 7.536133 | 0.493164 | 0.655273 | 0.063260 |
| ibm | readout_corrected |  |  | 7.564247 | 0.518122 | 0.673231 | 0.057248 |
| tdhf | mean_field | 1 | 0.1 | 8.000000 | 0.000000 | 0.855090 | 0.016260 |

## RMSE

| source | profile | reference | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---|---|---:|---:|---:|
| fire_opal | raw | tdhf:mean_field | 0.043999 | 0.075021 | 0.029251 |
| fire_opal | readout_corrected | tdhf:mean_field | 0.044329 | 0.075307 | 0.028930 |
| gaussian_u0 | free_fermion | tdhf:mean_field | 0.000373 | 0.001896 | 0.000849 |
| ibm | raw | tdhf:mean_field | 0.141055 | 0.235667 | 0.053688 |
| ibm | readout_corrected | tdhf:mean_field | 0.137932 | 0.221674 | 0.045760 |

## Artifacts

- normalized site observables: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/observable_comparison_shallow_t_only/cuprate_2d_site_observables_normalized.csv`
- normalized bond observables: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/observable_comparison_shallow_t_only/cuprate_2d_bond_observables_normalized.csv`

Claim boundary: these are diagonal observables only. d-wave pairing still needs separate off-diagonal measurement circuits.
