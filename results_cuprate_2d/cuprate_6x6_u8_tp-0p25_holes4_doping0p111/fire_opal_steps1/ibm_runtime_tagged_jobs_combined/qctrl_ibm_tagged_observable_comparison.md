# Q-CTRL tagged IBM Runtime observable comparison

Processed from IBM Runtime jobs with Q-CTRL tag while Fire Opal action API still reports PENDING.

## Site summaries

| source | profile | step | time | total charge | total spin-z | mean abs spin-z | mean doublon |
|---|---|---:|---:|---:|---:|---:|---:|
| gaussian_u0 | free_fermion | 1 | 0.1 | 32.000000 | -0.000000 | 0.836350 | 0.025179 |
| qctrl_ibm_tagged | raw |  |  | 35.617188 | -0.750000 | 0.045356 | 0.245877 |
| qctrl_ibm_tagged | readout_corrected |  |  | 35.970648 | -0.407636 | 0.053781 | 0.251017 |
| tdhf | mean_field | 1 | 0.1 | 32.000000 | -0.000000 | 0.838992 | 0.023967 |

## RMSE vs TDHF steps1

| source | profile | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---|---:|---:|---:|
| gaussian_u0 | free_fermion | 0.000195 | 0.002836 | 0.001297 |
| qctrl_ibm_tagged | raw | 0.335039 | 0.883660 | 0.226764 |
| qctrl_ibm_tagged | readout_corrected | 0.342371 | 0.877526 | 0.233584 |

Claim boundary: this is an IBM Runtime reconstruction from Q-CTRL-tagged jobs, not yet a Fire Opal action payload confirmation.
