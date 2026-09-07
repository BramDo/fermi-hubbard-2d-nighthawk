# 2D Cuprate Observable Comparison

All sources are normalized to the same site variables: `n_up`, `n_down`, `charge`, `spin_z`, `hole_density`, and `double_occupancy`.

## Site Summaries

| source | profile | step | time | total charge | total spin-z | mean abs spin-z | mean doublon |
|---|---|---:|---:|---:|---:|---:|---:|
| mps16 | mps_chi16 | 1 | 0.1 | 32.000000 | -0.000000 | 0.844895 | 0.021662 |
| mps32 | mps_chi32 | 1 | 0.1 | 32.000000 | 0.000000 | 0.840386 | 0.023625 |
| zne128 | zne_s128 | 1 | 0.1 | 32.436979 | -0.705717 | 0.718992 | 0.067902 |
| zne512 | zne_s512 | 1 | 0.1 | 32.003433 | -0.405742 | 0.715819 | 0.067631 |

## RMSE

| source | profile | reference | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---|---|---:|---:|---:|
| mps16 | mps_chi16 | mps32:mps_chi32 | 0.001034 | 0.005384 | 0.002231 |
| zne128 | zne_s128 | mps32:mps_chi32 | 0.137214 | 0.149804 | 0.057279 |
| zne512 | zne_s512 | mps32:mps_chi32 | 0.135975 | 0.151910 | 0.053021 |

## Artifacts

- normalized site observables: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/observable_comparison_ibm_phoenix_zne_s128_s512_vs_mps/cuprate_2d_site_observables_normalized.csv`

Claim boundary: these are diagonal observables only. d-wave pairing still needs separate off-diagonal measurement circuits.
