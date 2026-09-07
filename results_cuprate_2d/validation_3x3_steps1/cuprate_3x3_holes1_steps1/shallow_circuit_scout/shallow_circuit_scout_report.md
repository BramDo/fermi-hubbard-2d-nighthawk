# 3x3 2D Cuprate Shallow Circuit Scout

Local dry-run only. No IBM Runtime, Fire Opal, or hardware job was submitted.

The number-preserving ansatz rows are resource candidates. They preserve N_up/N_down ideally, but they omit row-major JW parity strings and are not validated Hubbard physics replacements yet.

## Resource Summary

| family | exact JW | logical 2q count | logical 2q depth | backend 2q count | backend 2q depth | ideal exact sector | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| explicit_jw | True | 786 | 589 | 2805 | 1723 | 1.000000 | 0.000466 | 0.001709 | 0.000759 |
| onsite_only | False | 9 | 1 | 18 | 2 | 1.000000 | 0.015053 | 0.042102 | 0.017236 |
| number_preserving_t_only | False | 33 | 5 | 159 | 52 | 1.000000 | 0.000462 | 0.001719 | 0.000808 |
| number_preserving_t_tprime | False | 49 | 9 | 287 | 119 | 1.000000 | 0.000516 | 0.001847 | 0.000803 |

## Artifacts

- resource summary: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/shallow_circuit_scout/shallow_circuit_resource_summary.csv`
- ideal site observables: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/shallow_circuit_scout/shallow_circuit_ideal_site_observables.csv`
- ideal observable summary: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/shallow_circuit_scout/shallow_circuit_ideal_observable_summary.csv`
- ideal RMSE: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/shallow_circuit_scout/shallow_circuit_ideal_observable_rmse.csv`
- metadata: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/shallow_circuit_scout/shallow_circuit_scout_metadata.json`
- backend candidates: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/shallow_circuit_scout/shallow_circuit_backend_candidates.csv`

Gate for next hardware submit: prefer a candidate only if backend two-qubit depth/count are materially lower and local/ideal observable drift is understood against TDHF.
