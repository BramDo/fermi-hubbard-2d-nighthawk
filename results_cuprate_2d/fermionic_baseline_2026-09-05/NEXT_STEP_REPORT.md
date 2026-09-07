# Next-step result: baseline not yet ready for a 72-qubit accuracy claim

The full t-t-prime-U network is numerically implemented and matches the stored QPY. The classical reference at total time 0.2 is not yet converged under the declared screening criteria.

| classical route | chi | seconds | retained norm weight | total charge | mean double occupancy |
|---|---:|---:|---:|---:|---:|
| routing-free MPO | 16 | 43.0 | 0.886828 | 32.00000000 | 0.063252 |
| routing-free MPO | 32 | 125.2 | 0.943970 | 32.00000000 | 0.068730 |
| direct gates | 16 | 26.5 | 0.439867 | 31.99999327 | 0.033735 |
| direct gates | 32 | 67.7 | 0.687467 | 32.00000811 | 0.055226 |
| direct gates | 64 | 204.1 | 0.828879 | 32.00000000 | 0.064102 |

Retained norm weight is not fidelity. Charge near 32 does not certify local accuracy. Timing covers each MPS evolution and its observables, not all validation/import/startup costs; it is not an end-to-end advantage comparison.

## What passed

- Direct MPS vs exact Qiskit statevectors on 2x2/2x3: maximum tested state distance 3.45e-14.
- Routing-free MPO vs the exact network on 2x2/2x3: maximum tested state distance 1.07e-14.
- Three explicit JW hopping MPO matrices match the reference gate matrices; all 16 engine/oracle checks passed.
- On the independent 2x3 Hamiltonian at fixed total time 0.2, halving dt reduces the state error by factors 4.049 and 4.012. Errors at dt=0.1/0.05/0.025 are 0.0134463/0.00332084/0.000827677. This is not a 6x6 convergence result.
- Artifact audit: 5 completed cases, 9 source snapshots, and all tested local probability bounds passed.

## What remains open

- Direct-gate chi 32 -> 64 differences: charge RMSE 0.004612, spin RMSE 0.024368, double-occupancy RMSE 0.009706; each exceeds the 0.001 target.
- Routing-free chi 16 -> 32 differences: charge RMSE 0.003385, spin RMSE 0.016261, double-occupancy RMSE 0.006331; also above target. No higher-chi result is implied by a partial run.
- Local limit reached for time0p2_dt0p1_mpo: Local MPO case exceeded 300.0 seconds. Partial progress is retained, not used as a completed reference.

The physics verification gate therefore stops promotion to a quantitative 72-qubit hardware benchmark. The 6x6 dt study is deferred because truncation error would currently contaminate it.
Next options are a larger or symmetry-aware classical convergence calculation, or an exact-reference smaller-lattice hardware-validation pilot. Neither hardware submission nor extra QPU spend has occurred. Failure of this bounded MPS study is not evidence of quantum advantage.
Future hardware settings remain in the previous sealed plans: 512 shots per noise factor and a five-second execution cap. The inherited shots=20000 field in the classical input is unused.

## Reproducible check

```text
python audit_cuprate_2d_fswap_baseline.py --root results_cuprate_2d/fermionic_baseline_2026-09-05
{"artifact_integrity_passed": true, "completed_cases": 5, "source_files_verified": 9, "hardware_accuracy_benchmark_ready": false, "reason": "Completed bond ladders do not satisfy the screening criteria; a controlled 6x6 dt study is still missing.", "qpu_jobs_submitted": 0}
```

Canonical MPS/MPO contraction API: https://quimb.readthedocs.io/en/main/autoapi/quimb/tensor/tn1d/core/index.html
