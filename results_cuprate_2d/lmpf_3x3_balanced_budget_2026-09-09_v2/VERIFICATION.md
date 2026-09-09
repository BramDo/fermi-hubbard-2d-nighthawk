# Executed verification of the corrected finite-calibration budget

Status: FINITE_CALIBRATION_KKT_COVARIANCE_AND_QISKIT_AUDIT_PASSED.

The physics-verification workflow materially changed this calculation:
an independent derivative check rejected the smooth approximation at tied
ZZ score extrema. v1 and its failure remain intact. v2 uses discrete future
calibration outcomes and the law of total covariance without a derivative.

## Analytic and provenance checks

Nine executed tests cover duration units, a nontrivial parallel circuit,
matched exposures, zero variance of constant scores, shared-mean difference
variance, fixed-weight1/sqrt(n), independent KKT/toy derivatives, a discrete
calibration mixture and its constant-calibration limit.
Full output: tests.txt.

The audit verifies all source/input/output hashes, actual provider QPYs and
their offline Qiskit Target durations. It replays all8192 binomial draws and
evaluates1,406 unique calibration outcomes with a separate scalar
assignment-matrix and KKT implementation. It reconstructs the full
conditional-average/calibration/total covariance and the paired contrasts.
Both Monte Carlo halves, low/high weight changes and timing scenarios agree.
No high-impact advantage claim, hardware run or model validation is made.

## Level5 executed independent audit

Command executed in WSL Ubuntu-Preview-C with one numerical thread:

```text
/usr/bin/timeout --signal=KILL 50s env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
/home/bram/.venvs/qiskit/bin/python -B lmpf_2d/verify_budget_calibration_mc.py
results_cuprate_2d/lmpf_3x3_balanced_budget_2026-09-09_v2
```

Exit code0. Actual output:

```json
{
  "status": "FINITE_CALIBRATION_KKT_COVARIANCE_AND_QISKIT_AUDIT_PASSED",
  "calibration_draws_replayed": 8192,
  "unique_calibration_outcomes_checked": 1406,
  "cases_checked": 4,
  "qpy_circuits_checked": 5,
  "maximum_differences": {
    "weights": 1.687538997430238e-14,
    "means": 9.992007221626409e-16,
    "covariance": 3.5388358909926865e-16
  },
  "checked_cases": [
    {"n": 64, "future_calibration_flag_pass_fraction": 1.0},
    {"n": 128, "future_calibration_flag_pass_fraction": 1.0},
    {"n": 256, "future_calibration_flag_pass_fraction": 0.9296875},
    {"n": 512, "future_calibration_flag_pass_fraction": 0.0}
  ],
  "new_qpu_seconds": 0,
  "authorization": false,
  "seconds": 9.002650792004715
}
```

This verifies implementation of the forecast, not calibration/model truth,
confidence-interval coverage, improved hardware accuracy or a guaranteed bill.
