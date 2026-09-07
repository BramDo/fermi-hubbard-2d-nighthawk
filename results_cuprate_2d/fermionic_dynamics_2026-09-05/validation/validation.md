# Full fermionic Hubbard dynamics validation

30 numerical checks passed.

Independent Fock-space Hamiltonian, exact sparse evolution, Qiskit statevectors and MPS agree within the stated checks.

| lattice | steps | time | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---:|---:|---:|---:|---:|
| 2x2 | 1 | 0.10 | 8.69354e-07 | 0.0039479 | 0.00193524 |
| 2x2 | 2 | 0.20 | 5.15995e-06 | 0.0122831 | 0.00560673 |
| 2x2 | 4 | 0.40 | 1.7669e-05 | 0.0179459 | 0.0053469 |
| 2x2 | 8 | 0.80 | 2.55772e-05 | 0.0260835 | 0.00480582 |
| 2x3 | 1 | 0.10 | 0.000117129 | 0.00162693 | 0.000763826 |
| 2x3 | 2 | 0.20 | 0.000333359 | 0.00523074 | 0.0022981 |
| 2x3 | 4 | 0.40 | 0.000641114 | 0.00827041 | 0.00254787 |
| 2x3 | 8 | 0.80 | 0.00119663 | 0.00415197 | 0.00114491 |

The RMSE here is Trotter error against exact full Hubbard evolution, without hardware noise.
Fixed-time dt refinement validates second-order convergence; this is not a quantum-advantage result.

All check values, thresholds, convergence rows and source hashes are in validation.json.
