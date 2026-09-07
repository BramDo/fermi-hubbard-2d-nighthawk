# 2D Cuprate Observable Comparison

All sources are normalized to the same site variables: `n_up`, `n_down`, `charge`, `spin_z`, `hole_density`, and `double_occupancy`.

## Site Summaries

| source | profile | step | time | total charge | total spin-z | mean abs spin-z | mean doublon |
|---|---|---:|---:|---:|---:|---:|---:|
| fire_opal | raw | 1 | 0.1 | 14.268756 | -0.061728 | 0.753977 | 0.055318 |
| fire_opal | readout_corrected | 1 | 0.1 | 14.103323 | 0.104219 | 0.764103 | 0.046188 |
| gaussian_u0 | free_fermion | 1 | 0.1 | 14.000000 | 0.000000 | 0.832662 | 0.020219 |
| ibm | raw | 1 | 0.1 | 13.766602 | -0.340820 | 0.650818 | 0.072632 |
| ibm | readout_corrected | 1 | 0.1 | 13.881690 | -0.242608 | 0.685372 | 0.064137 |
| mps | mps_chi64 | 1 | 0.1 | 14.000000 | 0.000000 | 0.833332 | 0.020170 |
| tdhf | mean_field | 1 | 0.1 | 14.000000 | 0.000000 | 0.834784 | 0.019260 |

## RMSE

| source | profile | reference | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---|---|---:|---:|---:|
| fire_opal | raw | mps:mps_chi64 | 0.065163 | 0.104742 | 0.045752 |
| fire_opal | readout_corrected | mps:mps_chi64 | 0.068299 | 0.097232 | 0.041630 |
| gaussian_u0 | free_fermion | mps:mps_chi64 | 0.000955 | 0.000917 | 0.000088 |
| ibm | raw | mps:mps_chi64 | 0.119908 | 0.218926 | 0.059685 |
| ibm | readout_corrected | mps:mps_chi64 | 0.130838 | 0.190883 | 0.056986 |
| tdhf | mean_field | mps:mps_chi64 | 0.000660 | 0.002011 | 0.000995 |

## Artifacts

- normalized site observables: `results_cuprate_2d/validation_ladder_steps1/cuprate_4x4_holes2_steps1/observable_comparison_shallow_t_only_steps1_vs_mps_fire_opal_qelib_retry/cuprate_2d_site_observables_normalized.csv`
- normalized bond observables: `results_cuprate_2d/validation_ladder_steps1/cuprate_4x4_holes2_steps1/observable_comparison_shallow_t_only_steps1_vs_mps_fire_opal_qelib_retry/cuprate_2d_bond_observables_normalized.csv`

Claim boundary: these are diagonal observables only. d-wave pairing still needs separate off-diagonal measurement circuits.
