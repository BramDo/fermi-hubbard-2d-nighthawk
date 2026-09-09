# Shot-aware variance penalty: verification

Executed in the existing WSL Qiskit environment:
```sh
python -B lmpf_2d/shot_aware.py --output results_cuprate_2d/lmpf_3x3_shot_aware_2026-09-09_v1
python -B lmpf_2d/verify_shot_aware.py results_cuprate_2d/lmpf_3x3_shot_aware_2026-09-09_v1
```

All 51 tests passed, including the analytic inverse-variance allocation limit,
agreement with the original scalar-ridge solver when all penalties are equal,
the range-variance bound, and rejection of invalid unpenalized Grams.

Selected actual independent audit output:
```text
status: SHOT_AWARE_ASSIGNMENT_KKT_AUDIT_PASSED
operators_checked: 3
bootstrap_replicates_checked: 10000
maximum_point_weight_error: 3.3306690738754696e-16
maximum_objective_error: 4.440892098500626e-16
maximum_penalties_error: 2.220446049250313e-16
maximum_weights_error: 1.9984014443252818e-15
maximum_pauli_error: 1.7763568394002505e-15
maximum_physical_error: 1.1657341758564144e-15
maximum_physical_frozen_weights_error: 7.216449660063518e-16
maximum_physical_fixed_calibration_error: 6.661338147750939e-16
calibration_dependent_weights_verified: true
paired_intervals_verified: true
historical_baselines_unchanged: true
new_qpu_seconds: 0
hardware_accuracy_validated: false
seconds: 1.2954417259988986
```

The auditor uses assignment-matrix solves to derive per-outcome score ranges
and direct KKT systems for the coefficients. The primary uncertainty recomputes
weights from each shared calibration draw, never target means or reference
errors. Frozen-weight and fixed-calibration variants are separately replayed.
Every saved bootstrap count/draw is matched to the previous pilot.

The new central point is [0.22146075168985047, -0.5272727142745836,
-0.16130742900028971] in charge/spin/doublon order. Its absolute errors are
smaller than the old fixed-ridge point for all three quantities, and its
bootstrap SDs are smaller. However, all nine paired improvement intervals
still include zero, and the new doublon point remains negative.
The lower doublon bound against old L-MPF is -0.0005447116940865307, not positive.

Software/evidence verification passes; a valid general hardware improvement,
rigorous total-error bound, full-profile/twirl validation or 6x6 result does not.
The reused-data nature and the model/truncation/small-shot limitations remain.
