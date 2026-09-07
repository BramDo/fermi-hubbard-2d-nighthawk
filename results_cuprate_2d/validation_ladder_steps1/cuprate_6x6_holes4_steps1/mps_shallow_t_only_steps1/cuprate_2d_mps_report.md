# 6x6 Cuprate MPS Circuit Baseline

This is a quimb MPS simulation of the same shallow circuit family used for the hardware route.
It is not a full Hamiltonian TDVP/ITensor convergence result.

## Target

- lattice/qubits: 6x6 / 72
- circuit_family: `number_preserving_t_only`
- steps/dt/time: 1/0.1/0.1

## Convergence

| max bond | observed max bond | elapsed s | occupation RMSE vs previous | total charge | total spin-z | mean doublon |
|---:|---:|---:|---:|---:|---:|---:|
| 16 | 16 | 6.630 | None | 32.000000 | -0.000000 | 0.021662 |
| 32 | 32 | 62.604 | 0.00274096674485996 | 32.000000 | 0.000000 | 0.023625 |

Claim boundary: this validates the shallow circuit tensor baseline only. Hardware output remains diagnostic until compared against this and other local baselines.
