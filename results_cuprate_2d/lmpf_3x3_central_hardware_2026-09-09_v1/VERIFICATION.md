# Central twirl0 hardware comparison: verification

Executed in the existing WSL Qiskit environment:
```sh
python -B lmpf_2d/single_twirl.py --output results_cuprate_2d/lmpf_3x3_central_hardware_2026-09-09_v1
python -B lmpf_2d/verify_single_twirl.py results_cuprate_2d/lmpf_3x3_central_hardware_2026-09-09_v1
```

All 45 regressions passed. Selected actual independent audit output:
```text
status: SINGLE_TWIRL_ASSIGNMENT_INVERSE_AUDIT_PASSED
methods_checked: 5
bootstrap_replicates_checked: 10000
maximum_point_physical_error: 2.220446049250313e-16
maximum_bootstrap_pauli_error: 1.5543122344752192e-15
maximum_bootstrap_physical_error: 8.881784197001252e-16
maximum_fixed_calibration_error: 6.661338147750939e-16
maximum_percentile_interval_error: 5.551115123125783e-16
matched_budget_verified: true
coefficient_and_subset_provenance_verified: true
paired_intervals_verified: true
new_qpu_seconds: 0
hardware_accuracy_validated: false
seconds: 0.8463432680000551
```

The independent route parses central bits by integer shifts, rebuilds observed
four-outcome counts and seeds, and solves the explicit two-bit assignment
matrix inverse. Occupation values are reconstructed via local joint
probabilities, independently of the production affine transform. Every saved
bootstrap replicate, point estimate, standard deviation and comparison interval
is checked. Original receipt/plan/data and coefficient source hashes are verified.

The matched-budget L-MPF physical point is
[-0.02946908745030452, -0.7128617466698439, -0.30947341190033584],
in central charge/spin/doublon order, versus the exact finite-circuit reference
[0.4046706253064062, -0.3620211851492071, 0.009685423195790493].
Negative charge/doublon estimates are preserved, not clipped.

All six paired absolute-error-improvement intervals include zero.
Software/evidence verification passes, but this pilot does not establish
improved hardware accuracy. Bootstrap intervals do not certify coverage with
only 7/14 folded shots or account for TN/model/drift/correlated-readout uncertainty.
No independent new hardware data, full-profile/eight-twirl validation or 6x6
result is claimed.
