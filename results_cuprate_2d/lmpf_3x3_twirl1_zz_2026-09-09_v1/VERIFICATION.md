# Partial verification after the ZZ time-budget stop

Overall status: INCOMPLETE_TIME_BUDGET. Saved partial evidence verified;
full convergence/stability and hardware accuracy NOT VALIDATED.

## Executed computation and actual stop

```bash
timeout --signal=KILL 600s env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /home/bram/.venvs/qiskit/bin/python -B lmpf_2d/twirl1_zz.py --output results_cuprate_2d/lmpf_3x3_twirl1_zz_2026-09-09_v1
```

Actual output:

```text
TESTS_PASSED 72
STATE_DONE 128 0 29.501
STATE_DONE 128 1 33.767
STATE_DONE 128 2 22.907
STATE_DONE 128 3 24.065
CHI_DONE 128 raw_F00 0.9799880399463387
STATE_DONE 256 0 132.701
STATE_DONE 256 1 148.461
STATE_DONE 256 2 139.851
TimeoutError: Local block deadline reached
```

Process exited1 due to the deliberate590s block deadline, before the outer
600s hard stop. The exception and no-retry flag remain in failure.json.
No complete fourth chi256 state, complete high-chi Gram or stability summary
is fabricated. The missing last-state in-memory work is not resumable, but all
seven prior complete states are preserved.

## Level 5: independent partial numerical check

```bash
timeout --signal=KILL 120s env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /home/bram/.venvs/qiskit/bin/python -B lmpf_2d/verify_twirl1_zz_partial.py results_cuprate_2d/lmpf_3x3_twirl1_zz_2026-09-09_v1
```

Actual output (selected fields; complete JSON retained):

```text
PARTIAL_SAVED_EVIDENCE_VERIFIED_NOT_CONVERGENCE
completed_states: 7
missing_state: chi256, arm3, factor3
independent_overlaps: 16
independent_complete_low_chi_fits: 1
maximum_low_chi_gram_error: 7.771561172376096e-16
maximum_low_chi_weight_error: 4.440892098500626e-15
largest_intermediate_elements: 262144
largest_estimated_flops: 1562378384
full_chi128_256_stability_available: false
hardware_accuracy_validated: false
new_qpu_seconds: 0
audit_seconds: 6.30049930700261

Archive status: PASS
selected_originals: 3
verified_objects: 3
restored: 0
already_present: 3
archive_seconds: 7.862537947999954
```

The partial-audit process exited0. It uses independently ordered raw tensor
contractions for all available pairs, with the explicit3e9 FLOP/2^22-element
guard. A direct KKT solve verifies the COMPLETE low-chi fit. No reduced-arm
high-chi fit is performed: the3x3 partial Gram is not a substitute for the
required four-arm matrix.

Both central calibration modes enter an independent4x4 assignment-matrix
inversion for the ZZ score range. Five added tests cover joint support,
mask parity, unequal/asymmetric errors, dependence on both modes, zero-readout
limit, invalid inputs, explicit guard delegation and the nonmultiplicativity
of a noisy Heisenberg channel. Earlier67 tests remain included, total72.

All seven saved-state byte hashes, numerical-source snapshots, frozen inputs,
mask signs and relevant QPY hashes are checked. partial_grams.json names exactly
which arms are available. partial_manifest.json preserves the generated data,
source and archive hashes, including the raw large-state hashes. No orphan
or incomplete state file was accepted.

## Scope and inference limits

Normalized Hilbert-Schmidt overlaps are dimensionless, Tr(A-dagger B)/2^18.
The ideal Pauli-string norm is exactly1, independent of the target state;
retaining this identity does not fill in an absent noisy arm or certify
the surrogate against hardware. Low-chi PSD and fit checks are preserved.

Full low/high G, b and coefficient-change gates are unavailable. Their flags
are null, not true or a numerical zero. No target values have been scored,
no8-twirl aggregate is formed and no6x6 extension is permitted by this result.

A separate bounded calculation of ONLY the missing chi256/factor3 state
is required before the already prepared full audit can run.
