# 2D Cuprate Observable Comparison

All sources are normalized to the same site variables: `n_up`, `n_down`, `charge`, `spin_z`, `hole_density`, and `double_occupancy`.

## Site Summaries

| source | profile | step | time | total charge | total spin-z | mean abs spin-z | mean doublon |
|---|---|---:|---:|---:|---:|---:|---:|
| fire_opal | raw |  |  | 8.493671 | 0.295034 | 0.388294 | 0.180569 |
| fire_opal | readout_corrected |  |  | 8.481839 | 0.315028 | 0.386834 | 0.180117 |
| gaussian_u0 | free_fermion | 1 | 0.1 | 8.000000 | 0.000000 | 0.853300 | 0.017061 |
| ibm | raw |  |  | 7.234375 | 0.117188 | 0.076606 | 0.171332 |
| ibm | readout_corrected |  |  | 7.219384 | 0.176720 | 0.084416 | 0.170556 |
| tdhf | mean_field | 1 | 0.1 | 8.000000 | 0.000000 | 0.855090 | 0.016260 |

## RMSE

| source | profile | reference | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---|---|---:|---:|---:|
| fire_opal | raw | tdhf:mean_field | 0.248265 | 0.501067 | 0.177270 |
| fire_opal | readout_corrected | tdhf:mean_field | 0.248101 | 0.502361 | 0.176896 |
| gaussian_u0 | free_fermion | tdhf:mean_field | 0.000373 | 0.001896 | 0.000849 |
| ibm | raw | tdhf:mean_field | 0.370618 | 0.864282 | 0.168553 |
| ibm | readout_corrected | tdhf:mean_field | 0.373144 | 0.868128 | 0.167732 |

## Artifacts

- normalized site observables: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/observable_comparison/cuprate_2d_site_observables_normalized.csv`
- normalized bond observables: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/observable_comparison/cuprate_2d_bond_observables_normalized.csv`

Claim boundary: these are diagonal observables only. d-wave pairing still needs separate off-diagonal measurement circuits.
