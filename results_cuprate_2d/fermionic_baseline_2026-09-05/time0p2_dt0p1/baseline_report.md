# Full fermionic network: classical baseline screening

Engine validation: 9 checks passed.
Two consecutive bond refinements pass: False.

| chi | elapsed s | retained norm weight | N-up | N-down | half-chain entropy (bits) |
|---:|---:|---:|---:|---:|---:|
| 16 | 26.50 | 0.43986676 | 15.999998 | 15.999995 | 1.321643 |
| 32 | 67.72 | 0.68746687 | 16.000004 | 16.000004 | 1.379693 |
| 64 | 204.13 | 0.82887936 | 16.000000 | 16.000000 | 1.483891 |

## Observable differences

| chi pair | charge RMSE | spin-z RMSE | double-occupancy RMSE | screening passes |
|---|---:|---:|---:|---|
| 16 -> 32 | 0.00905244 | 0.0560273 | 0.0232226 | False |
| 32 -> 64 | 0.00461212 | 0.024368 | 0.00970609 | False |

Screening thresholds: RMSE <= 0.001 and maximum site difference <= 0.005 for each observable; each mean spin particle number within 0.01, retained norm weight >= 0.99.
A pass is a finite-ladder diagnostic, not a certified error bound. Retained norm weight is not fidelity. Mean particle-number conservation alone is not sector purity.
The initial state, t, t-prime, U and network ordering match the mapped full-fermion circuit. Spin-z denotes n-up minus n-down; physical S-z is half this value.
Time uses hbar/t with hopping_t=1. Statistics/shots do not enter this noiseless calculation.
Do not compare the old shallow hardware data against this reference. No QPU jobs are submitted.
MPS method reference: https://quimb.readthedocs.io/en/main/autoapi/quimb/tensor/tn1d/core/index.html
