# IBM best-mit observable comparison

Time-matched against TDHF steps1.

## Site summaries

| source | profile | step | time | total charge | total spin-z | mean abs spin-z | mean doublon |
|---|---|---:|---:|---:|---:|---:|---:|
| gaussian_u0 | free_fermion | 1 | 0.1 | 32.000000 | -0.000000 | 0.836350 | 0.025179 |
| ibm_best_mit | raw |  |  | 17.526367 | -0.547852 | 0.104791 | 0.084581 |
| ibm_best_mit | readout_corrected |  |  | 16.953522 | -0.497634 | 0.112525 | 0.082851 |
| tdhf | mean_field | 1 | 0.1 | 32.000000 | -0.000000 | 0.838992 | 0.023967 |

## RMSE vs TDHF steps1

| source | profile | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---|---:|---:|---:|
| gaussian_u0 | free_fermion | 0.000195 | 0.002836 | 0.001297 |
| ibm_best_mit | raw | 0.626647 | 0.881339 | 0.105383 |
| ibm_best_mit | readout_corrected | 0.644396 | 0.866942 | 0.106709 |
