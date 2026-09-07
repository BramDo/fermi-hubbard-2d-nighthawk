# 4x4 Cuprate MPS Circuit Baseline

This is a quimb MPS simulation of the same shallow circuit family used for the hardware route.
It is not a full Hamiltonian TDVP/ITensor convergence result.

## Target

- lattice/qubits: 4x4 / 32
- circuit_family: `number_preserving_t_only`
- steps/dt/time: 1/0.1/0.1

## Convergence

| max bond | observed max bond | elapsed s | occupation RMSE vs previous | total charge | total spin-z | mean doublon |
|---:|---:|---:|---:|---:|---:|---:|
| 32 | 32 | 13.497 | None | 14.000000 | 0.000000 | 0.020073 |
| 64 | 64 | 49.455 | 0.000202737115744488 | 14.000000 | 0.000000 | 0.020170 |

Claim boundary: this validates the shallow circuit tensor baseline only. Hardware output remains diagnostic until compared against this and other local baselines.
