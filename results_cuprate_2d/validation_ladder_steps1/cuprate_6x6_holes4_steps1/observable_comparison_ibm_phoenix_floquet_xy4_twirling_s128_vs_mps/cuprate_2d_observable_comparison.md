# 2D Cuprate Observable Comparison

All sources are normalized to the same site variables: `n_up`, `n_down`, `charge`, `spin_z`, `hole_density`, and `double_occupancy`.

## Site Summaries

| source | profile | step | time | total charge | total spin-z | mean abs spin-z | mean doublon |
|---|---|---:|---:|---:|---:|---:|---:|
| gaussian_u0 | free_fermion | 1 | 0.1 | 32.000000 | -0.000000 | 0.836350 | 0.025179 |
| ibm | raw | 1 | 0.1 | 33.414062 | -0.554688 | 0.562717 | 0.128255 |
| ibm | readout_corrected | 1 | 0.1 | 34.018315 | -0.566423 | 0.576299 | 0.131602 |
| mps16 | mps_chi16 | 1 | 0.1 | 32.000000 | -0.000000 | 0.844895 | 0.021662 |
| mps32 | mps_chi32 | 1 | 0.1 | 32.000000 | 0.000000 | 0.840386 | 0.023625 |
| tdhf | mean_field | 1 | 0.1 | 32.000000 | -0.000000 | 0.838992 | 0.023967 |

## RMSE

| source | profile | reference | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---|---|---:|---:|---:|
| gaussian_u0 | free_fermion | mps32:mps_chi32 | 0.001181 | 0.004429 | 0.001750 |
| ibm | raw | mps32:mps_chi32 | 0.225324 | 0.333308 | 0.114316 |
| ibm | readout_corrected | mps32:mps_chi32 | 0.223382 | 0.318909 | 0.117927 |
| mps16 | mps_chi16 | mps32:mps_chi32 | 0.001034 | 0.005384 | 0.002231 |
| tdhf | mean_field | mps32:mps_chi32 | 0.001003 | 0.001905 | 0.000682 |

## Artifacts

- normalized site observables: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/observable_comparison_ibm_phoenix_floquet_xy4_twirling_s128_vs_mps/cuprate_2d_site_observables_normalized.csv`
- normalized bond observables: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/observable_comparison_ibm_phoenix_floquet_xy4_twirling_s128_vs_mps/cuprate_2d_bond_observables_normalized.csv`

Claim boundary: these are diagonal observables only. d-wave pairing still needs separate off-diagonal measurement circuits.
