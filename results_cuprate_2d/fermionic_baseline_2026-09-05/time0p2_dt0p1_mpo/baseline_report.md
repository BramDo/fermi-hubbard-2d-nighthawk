# Full fermionic network: classical baseline screening

Engine validation: 16 checks passed.
Two consecutive bond refinements pass: False.

| chi | elapsed s | retained norm weight | N-up | N-down | half-chain entropy (bits) |
|---:|---:|---:|---:|---:|---:|
| 16 | 42.96 | 0.88682818 | 16.000000 | 16.000000 | 1.373576 |
| 32 | 125.24 | 0.94397011 | 16.000000 | 16.000000 | 1.558275 |

## Observable differences

| chi pair | charge RMSE | spin-z RMSE | double-occupancy RMSE | screening passes |
|---|---:|---:|---:|---|
| 16 -> 32 | 0.00338514 | 0.0162614 | 0.00633136 | False |

Screening thresholds: RMSE <= 0.001 and maximum site difference <= 0.005 for each observable; each mean spin particle number within 0.01, retained norm weight >= 0.99.
A pass is a finite-ladder diagnostic, not a certified error bound. Retained norm weight is not fidelity. Mean particle-number conservation alone is not sector purity.
The initial state, t, t-prime, U and network ordering match the mapped full-fermion circuit. Spin-z denotes n-up minus n-down; physical S-z is half this value.
Time uses hbar/t with hopping_t=1. Statistics/shots do not enter this noiseless calculation.
Do not compare the old shallow hardware data against this reference. No QPU jobs are submitted.
MPS method reference: https://quimb.readthedocs.io/en/main/autoapi/quimb/tensor/tn1d/core/index.html
