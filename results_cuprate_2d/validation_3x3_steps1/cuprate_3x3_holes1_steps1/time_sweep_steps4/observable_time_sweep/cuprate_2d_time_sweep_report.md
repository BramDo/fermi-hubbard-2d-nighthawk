# 3x3 2D Cuprate Time Sweep

Reference source for RMSE: `exact_full`.
All rows use diagonal site observables only: charge, spin-z, hole density, and doublon.

## RMSE by Step

| step | source | profile | charge RMSE | spin-z RMSE | doublon RMSE |
|---:|---|---|---:|---:|---:|
| 0 | exact_t_only | fixed_sector | 0.000000 | 0.000000 | 0.000000 |
| 1 | exact_t_only | fixed_sector | 0.000519 | 0.000896 | 0.000079 |
| 2 | exact_t_only | fixed_sector | 0.001871 | 0.003245 | 0.000982 |
| 3 | exact_t_only | fixed_sector | 0.013111 | 0.006454 | 0.003472 |
| 4 | exact_t_only | fixed_sector | 0.031148 | 0.009996 | 0.007165 |
| 0 | gaussian_u0 | free_fermion | 0.000000 | 0.000000 | 0.000000 |
| 1 | gaussian_u0 | free_fermion | 0.000378 | 0.001924 | 0.000889 |
| 2 | gaussian_u0 | free_fermion | 0.005167 | 0.026965 | 0.011859 |
| 3 | gaussian_u0 | free_fermion | 0.019970 | 0.109488 | 0.044513 |
| 4 | gaussian_u0 | free_fermion | 0.042469 | 0.254813 | 0.093432 |
| 0 | tdhf | mean_field | 0.000000 | 0.000000 | 0.000000 |
| 1 | tdhf | mean_field | 0.000004 | 0.000029 | 0.000040 |
| 2 | tdhf | mean_field | 0.000196 | 0.001375 | 0.001822 |
| 3 | tdhf | mean_field | 0.001202 | 0.008724 | 0.011952 |
| 4 | tdhf | mean_field | 0.003642 | 0.019529 | 0.032194 |

## Site Summary by Step

| step | source | profile | total charge | total spin-z | mean |spin-z| | mean doublon |
|---:|---|---|---:|---:|---:|---:|
| 0 | exact_full | fixed_sector | 8.000000 | 0.000000 | 0.888889 | 0.000000 |
| 1 | exact_full | fixed_sector | 8.000000 | 0.000000 | 0.855116 | 0.016223 |
| 2 | exact_full | fixed_sector | 8.000000 | 0.000000 | 0.778109 | 0.049209 |
| 3 | exact_full | fixed_sector | 8.000000 | -0.000000 | 0.707763 | 0.069466 |
| 4 | exact_full | fixed_sector | 8.000000 | -0.000000 | 0.674849 | 0.064354 |
| 0 | exact_t_only | fixed_sector | 8.000000 | 0.000000 | 0.888889 | 0.000000 |
| 1 | exact_t_only | fixed_sector | 8.000000 | 0.000000 | 0.855648 | 0.016165 |
| 2 | exact_t_only | fixed_sector | 8.000000 | -0.000000 | 0.779968 | 0.048543 |
| 3 | exact_t_only | fixed_sector | 8.000000 | 0.000000 | 0.711005 | 0.067535 |
| 4 | exact_t_only | fixed_sector | 8.000000 | -0.000000 | 0.678740 | 0.061556 |
| 0 | gaussian_u0 | free_fermion | 8.000000 | 0.000000 | 0.888889 | 0.000000 |
| 1 | gaussian_u0 | free_fermion | 8.000000 | 0.000000 | 0.853300 | 0.017061 |
| 2 | gaussian_u0 | free_fermion | 8.000000 | 0.000000 | 0.752594 | 0.060474 |
| 3 | gaussian_u0 | free_fermion | 8.000000 | -0.000000 | 0.603497 | 0.112242 |
| 4 | gaussian_u0 | free_fermion | 8.000000 | -0.000000 | 0.429443 | 0.155495 |
| 0 | tdhf | mean_field | 8.000000 | 0.000000 | 0.888889 | 0.000000 |
| 1 | tdhf | mean_field | 8.000000 | 0.000000 | 0.855090 | 0.016260 |
| 2 | tdhf | mean_field | 8.000000 | 0.000000 | 0.776874 | 0.050905 |
| 3 | tdhf | mean_field | 8.000000 | 0.000000 | 0.699948 | 0.080622 |
| 4 | tdhf | mean_field | 8.000000 | -0.000000 | 0.657438 | 0.094534 |

## Artifacts

- site observables: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/time_sweep_steps4/observable_time_sweep/cuprate_2d_time_sweep_site_observables.csv`
- summary CSV: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/time_sweep_steps4/observable_time_sweep/cuprate_2d_time_sweep_summary.csv`
- RMSE CSV: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/time_sweep_steps4/observable_time_sweep/cuprate_2d_time_sweep_rmse.csv`

Claim boundary: this is a local small-rung diagonal-observable time sweep. It is not a hardware result and it does not measure off-diagonal d-wave pairing.
