# Executed verification: frozen twirl1 noise-model diagnostic

Status: FROZEN_MODEL_RAW_TN_AND_ASSIGNMENT_AUDIT_PASSED.
This verifies implementation and provenance, not hardware accuracy or a
causal error explanation. The physics-verification workflow kept reference,
TN truncation, device-model mismatch and finite-shot uncertainty separate.

## Level 1: artifacts and scope

The main runner snapshots sources and the prepared protocol before calculation.
The audit checks the output manifest, source snapshots, current source hashes,
parent results, independent parent verification and all 12 state NPZ/metadata
hashes. Model states are fixed to chi128 for Z_up/Z_down, chi256 for ZZ, twirl1,
the original job, masks and actual native circuits. The original raw bitstrings
are compared directly with the selected input copies. No remote service is called.

The first verifier attempt's JSON key TypeError is preserved in
../lmpf_3x3_twirl1_noise_model_2026-09-09_v1/verification/attempt_failure.json.
A regression test exercises string-valued support keys in v2.

## Level 2: unit and integration tests

Actual main stdout: TESTS_PASSED 84.
Full executed unittest output is in tests.txt.
New tests check 64/7/14 arm aggregation, independent readout inversion,
normalization/exponent retention, invalid shot counts, singular readout guards,
marginal interval endpoints and JSON support-key handling.

## Level 3: independent numerical path

Production means use a left-to-right MPS-chain contraction.
The audit adds local [1,0,0,1] functionals to the raw TN and uses a separately
built bounded contraction tree. There is no shared chain contraction routine,
unit-norm rescaling, extra state preparation or dense 4^18 object.

Production readout correction uses moment functions; the audit explicitly
builds each 4x4 assignment matrix, solves its transpose for joint probabilities,
then applies the masks. All original counts and all bootstrap seeds are replayed.

## Level 4: physical and statistical reporting checks

Both paths check central charge, spin and doublons, the joint probabilities,
fixed-calibration SDs, shared 9x9 Pauli covariance, marginal intervals and flags.
All 12 model means retain their original scale. All four reconstructed model
joint distributions pass the local range check; no observed estimate or
bootstrap tail is clipped. Exact finite-circuit references remain diagnostic
inputs, not fitting targets. Raw ZZ Gram instability remains disclosed.

Noisy factor2 ZZ flags a marginal discrepancy; the result explicitly retains
the post-hoc, unadjusted, seven-shot and incomplete-uncertainty caveats.
No model-validation, causal attribution or 6x6-go flag is asserted.

## Level 5: actual independent execution

Command executed in WSL Ubuntu-Preview-C, single numerical thread:

```text
/usr/bin/timeout --signal=KILL 45s env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
/home/bram/.venvs/qiskit/bin/python -B lmpf_2d/verify_twirl1_noise_check.py
results_cuprate_2d/lmpf_3x3_twirl1_noise_model_2026-09-09_v2
```

Exit code: 0. Selected fields from actual stdout, with the complete result in
verification/verification.json:

```json
{
  "status": "FROZEN_MODEL_RAW_TN_AND_ASSIGNMENT_AUDIT_PASSED",
  "saved_operator_means_verified": 12,
  "bootstrap_replicates_replayed": 10000,
  "maximum_model_contraction_difference": 8.326672684688674e-16,
  "maximum_pauli_error": 6.661338147750939e-16,
  "maximum_physical_error": 4.440892098500626e-16,
  "maximum_pauli_fixed_calibration_error": 3.3306690738754696e-16,
  "maximum_pauli_minus_model_error": 1.2212453270876722e-15,
  "full64_7_14_arm_counts_verified": true,
  "source_and_input_hashes_verified": true,
  "shared_calibration_verified": true,
  "no_model_rescaling_or_clipping": true,
  "new_qpu_seconds": 0,
  "new_tn_states": 0,
  "noise_model_validated": false,
  "seconds": 6.296219978001318
}
```

The v1 and v2 bootstrap NPZ SHA256 values were also compared independently
with PowerShell Get-FileHash: identical, 2,507,994 bytes each.
The first attempt is retained, not retrospectively labeled as audit-passed.
