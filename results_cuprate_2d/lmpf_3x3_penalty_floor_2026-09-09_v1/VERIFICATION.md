# Executed verification: same-shot penalty-floor comparison

Status: PENALTY_FLOOR_ACTUAL_SHOT_KKT_AUDIT_PASSED.
Numerical correctness and exploratory screening do not establish physical accuracy.

## Tests and invariants

15 tests passed: the earlier9 budget/calibration tests and6 new floor tests.
New checks cover the denominator rule; d=n identity and zero variance of
equal same-sample estimators; fixed-weight conditional scaling with invariant
calibration covariance; independent small-mixture actual-shot covariance;
normalized joint probabilities with retained negatives; invalid array shapes.

All8192 saved calibration counts are replayed exactly.
An independent assignment-matrix/KKT oracle recomputes weights at64/128
and original256/512 on1406 unique calibrations. Actual target-shot covariance
uses a separate16x16 block count covariance with[n,2n,n,n], then the combined
15-output transfer map. It does not substitute the penalty denominator
for the real shot count.

Source/input/output hashes, all forecast means, full and paired covariance,
stability fractions, physical-probability fractions, Monte Carlo halves,
candidate screening and unchanged archived time scenarios are verified.
No probabilities or failed candidates were clipped.

## Level5 independent execution

Executed in WSL Ubuntu-Preview-C, one numerical thread:

```text
/usr/bin/timeout --signal=KILL 60s env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
/home/bram/.venvs/qiskit/bin/python -B lmpf_2d/verify_penalty_floor.py
results_cuprate_2d/lmpf_3x3_penalty_floor_2026-09-09_v1
```

Exit code0. Actual stdout:

```json
{
  "status": "PENALTY_FLOOR_ACTUAL_SHOT_KKT_AUDIT_PASSED",
  "cases_checked": 4,
  "calibration_draws_replayed": 8192,
  "unique_calibration_outcomes": 1406,
  "joint_covariance_dimensions": [15,15],
  "maximum_differences": {
    "weights": 4.6074255521944e-15,
    "means": 9.992007221626409e-16,
    "covariance": 2.949029909160572e-16
  },
  "candidate_checks": [
    {"n":256,"cap":64,"weight_stability_fraction":1.0,"conditional_physical_fraction":1.0},
    {"n":256,"cap":128,"weight_stability_fraction":1.0,"conditional_physical_fraction":0.421630859375},
    {"n":512,"cap":64,"weight_stability_fraction":1.0,"conditional_physical_fraction":1.0},
    {"n":512,"cap":128,"weight_stability_fraction":1.0,"conditional_physical_fraction":0.421630859375}
  ],
  "new_qpu_seconds": 0,
  "accuracy_improvement_proven": false,
  "seconds": 9.692084171998431
}
```

The complete machine-readable result is in verification/verification.json.
Hardware draft documents added after numerical verification are planning
artifacts only. They are not submission receipts or granted authority.
