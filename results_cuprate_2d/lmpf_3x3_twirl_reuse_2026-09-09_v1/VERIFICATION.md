# Verification: archived-twirl reuse gate

Status: numerical/matrix diagnostic verified; hardware robustness NOT validated.

## Executed independent computation (Level 5)

Environment: Ubuntu-Preview-C, /home/bram/.venvs/qiskit/bin/python,
OPENBLAS_NUM_THREADS=1, OMP_NUM_THREADS=1, threadpool_limits(1).
No cloud service, new QPU job, target scoring, dense 18-qubit operator or new TN.

Executed from repository root:

```bash
python -B lmpf_2d/twirl_reuse_check.py --output results_cuprate_2d/lmpf_3x3_twirl_reuse_2026-09-09_v1
python -B lmpf_2d/verify_twirl_reuse.py results_cuprate_2d/lmpf_3x3_twirl_reuse_2026-09-09_v1
```

Actual output (selected fields; complete output in summary.json/verification.json):

```text
NO_TWIRL0_REUSE_ESTABLISHED
target_circuits: 24
internal_mismatch_pairs: 21
full_surrogate_channels_distinguished: 21
tests_run: 58
elapsed_seconds: 12.498235809998732
new_qpu_seconds: 0

TWIRL_REUSE_MATRIX_AUDIT_PASSED
native_circuits: 24
comparison_pairs: 21
unique_local_matrices: 130
maximum_archive_logdet_error: 1.7763568394002505e-15
maximum_local_matrix_logdet_error: 2.2204460492503128e-16
dense_three_qubit_checks: 6
maximum_dense_logdet_error: 2.0816681711721685e-16
all_source_input_output_hashes_verified: true
hardware_robustness_validated: false
elapsed_seconds: 2.9381590880002477
```

The audit uses explicit U-dagger P U matrices and Pauli traces rather than
the production PTM constructor. It composes full 64x64 adjoint channels for
the three-qubit oracle, tests reversed CZ qargs and final unmasking, and
reconstructs archived calibration rates independently with math.log1p.

## Bounds and exclusions

All quantities in the determinant formula are dimensionless. The zero-noise
limit is zero. Unitary conjugations have absolute determinant one. Product
determinants do not assume commutation. Comparison threshold 1e-10 exceeds
observed roundoff by five orders of magnitude, while the smallest archive
difference is about 4.82e-4.

Source, bound/provider QPY and layout checks preserve the actual native inputs.
The underlying noise remains the SAME surrogate used previously, not a learned
or experimentally certified device channel. Different full channels need not
differ on every selected Pauli; no observable-error bound follows from logdet.

The gate FAILURE is preserved: terminal-only reuse is not established. Passing
58 implementation tests is not passing the hardware-accuracy gate. No clipping,
retuning, seed selection, fixed-sector projection, or reference-assisted fit.
Other archived twirls have appeared in historical aggregate analyses, so a
future robustness comparison is reused-data validation, not a blinded holdout.

