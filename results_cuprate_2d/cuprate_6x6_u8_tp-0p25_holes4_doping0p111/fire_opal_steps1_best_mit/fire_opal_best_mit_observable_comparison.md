# 2D Cuprate Observable Comparison

All sources are normalized to the same site variables: `n_up`, `n_down`, `charge`, `spin_z`, `hole_density`, and `double_occupancy`.

## Site Summaries

| source | profile | step | time | total charge | total spin-z | mean abs spin-z | mean doublon |
|---|---|---:|---:|---:|---:|---:|---:|
| fire_opal_best_mit | raw |  |  | 36.298828 | -0.101562 | 0.030707 | 0.252170 |
| fire_opal_best_mit | readout_corrected |  |  | 36.266871 | -0.129124 | 0.030806 | 0.251705 |
| gaussian_u0 | free_fermion_step1 | 1 | 0.1 | 32.000000 | -0.000000 | 0.836350 | 0.025179 |
| ibm_best_mit | raw |  |  | 17.526367 | -0.547852 | 0.104791 | 0.084581 |
| ibm_best_mit | readout_corrected |  |  | 16.953522 | -0.497634 | 0.112525 | 0.082851 |
| tdhf | mean_field_step1 | 1 | 0.1 | 32.000000 | -0.000000 | 0.838992 | 0.023967 |

## RMSE

| source | profile | reference | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---|---|---:|---:|---:|
| fire_opal_best_mit | raw | tdhf:mean_field_step1 | 0.321863 | 0.889892 | 0.229493 |
| fire_opal_best_mit | readout_corrected | tdhf:mean_field_step1 | 0.320336 | 0.888265 | 0.229077 |
| gaussian_u0 | free_fermion_step1 | tdhf:mean_field_step1 | 0.000195 | 0.002836 | 0.001297 |
| ibm_best_mit | raw | tdhf:mean_field_step1 | 0.626647 | 0.881339 | 0.105383 |
| ibm_best_mit | readout_corrected | tdhf:mean_field_step1 | 0.644396 | 0.866942 | 0.106709 |

## Artifacts

- normalized site observables: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/fire_opal_steps1_best_mit/fire_opal_best_mit_site_observables_normalized.csv`
- normalized bond observables: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/fire_opal_steps1_best_mit/fire_opal_best_mit_bond_observables_normalized.csv`

Claim boundary: these are diagonal observables only. d-wave pairing still needs separate off-diagonal measurement circuits.

## Best-Mit Note

Baseline rows are fixed to `step=1` (`time=0.1`) to match the submitted one-step hardware jobs. Fire Opal was retrieved from existing action IDs only; no new jobs were submitted in this retrieval pass.

## Bond Summary

| source | profile | orientation | bonds | mean charge corr | mean spin-z corr | mean abs spin-z corr |
|---|---|---|---:|---:|---:|---:|
| ibm_best_mit | raw | x | 30 | 0.352181 | -0.004590 | 0.018717 |
| ibm_best_mit | raw | y | 30 | 0.294010 | -0.002799 | 0.020833 |
| ibm_best_mit | readout_corrected | x | 30 | 0.340361 | -0.006164 | 0.021644 |
| ibm_best_mit | readout_corrected | y | 30 | 0.284909 | -0.002414 | 0.023867 |
| fire_opal_best_mit | raw | x | 30 | 1.014421 | 0.005436 | 0.011947 |
| fire_opal_best_mit | raw | y | 30 | 1.017448 | -0.001042 | 0.014258 |
| fire_opal_best_mit | readout_corrected | x | 30 | 1.012075 | 0.005555 | 0.012039 |
| fire_opal_best_mit | readout_corrected | y | 30 | 1.015659 | -0.001035 | 0.014297 |
