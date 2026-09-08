# Verification: application correct, acceptance gate failed

Executed command (WSL, existing qiskit environment):

```sh
python -B lmpf_2d/verify_archive_3x3.py results_cuprate_2d/lmpf_3x3_hardware_2026-09-08_v1
```

Selected actual output:

```text
status: VERIFIED_3X3_EXPLORATORY_APPLICATION_NOT_ACCEPTED_FOR_6X6
maximum_gram_reconstruction_error: 8.881784197001252e-16
maximum_optimizer_projected_gradient: 3.3306690738754696e-16
maximum_raw_sample_reconstruction_error: 6.661338147750939e-16
native_quimb_chi1_squared_distance: 0.0
native_quimb_bp_nonconverged_updates: 0
states_saved: 80
physical_observables: 27
six_by_six_started: false
new_qpu_seconds: 0
```

This is an executed NumPy/Qiskit/quimb cross-check, not an analytic or Lean
proof. Norm-squared cancellation at floating precision is reported as 0.0;
the acceptance tolerance was 1e-10. The independent native check covers one
observable at chi=1, not convergence at larger chi or every native operator.

The main run's 27 tests passed. Saved finite-circuit ideal controls, raw
bitstrings, reconstructed observables, fit constraints, complete cross-twirl
Grams, paired-bootstrap intervals and source/input/result hashes were checked.
Higher-bond and device-noise-model validation remain open. Empirical lading
and doublon guardrails fail, so 6x6 was deliberately not started.

Full machine-readable output: [verification.json](verification/verification.json).
