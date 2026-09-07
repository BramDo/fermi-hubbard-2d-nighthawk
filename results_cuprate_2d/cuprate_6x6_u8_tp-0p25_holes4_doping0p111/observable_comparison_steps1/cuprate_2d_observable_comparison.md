# 2D Cuprate Observable Comparison

All sources are normalized to the same site variables: `n_up`, `n_down`, `charge`, `spin_z`, `hole_density`, and `double_occupancy`.

## Site Summaries

| source | profile | step | time | total charge | total spin-z | mean abs spin-z | mean doublon |
|---|---|---:|---:|---:|---:|---:|---:|
| gaussian_u0 | free_fermion | 1 | 0.1 | 32.000000 | -0.000000 | 0.836350 | 0.025179 |
| ibm | raw |  |  | 12.503906 | 0.378906 | 0.103407 | 0.049154 |
| ibm | readout_corrected |  |  | 11.897078 | 0.650545 | 0.108421 | 0.045790 |
| tdhf | mean_field | 1 | 0.1 | 32.000000 | -0.000000 | 0.838992 | 0.023967 |

## RMSE

| source | profile | reference | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---|---|---:|---:|---:|
| gaussian_u0 | free_fermion | tdhf:mean_field | 0.000195 | 0.002836 | 0.001297 |
| ibm | raw | tdhf:mean_field | 0.722951 | 0.879802 | 0.074047 |
| ibm | readout_corrected | tdhf:mean_field | 0.734495 | 0.880750 | 0.072745 |

## Artifacts

- normalized site observables: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/observable_comparison_steps1/cuprate_2d_site_observables_normalized.csv`
- normalized bond observables: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/observable_comparison_steps1/cuprate_2d_bond_observables_normalized.csv`

Claim boundary: these are diagonal observables only. d-wave pairing still needs separate off-diagonal measurement circuits.
