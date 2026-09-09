# Verification: complete ZZ after one-arm resumption

Status: full independent numerical audit PASSED; predefined exact-norm local
flags PASSED; raw full-Gram flag FAILED; hardware accuracy NOT VALIDATED.

## Executed commands and oracle output (Level 5)

WSL Ubuntu-Preview-C, existing /home/bram/.venvs/qiskit/bin/python,
one numerical thread; versions and hashes in plan.json.

```bash
timeout --signal=KILL 300s env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /home/bram/.venvs/qiskit/bin/python -B lmpf_2d/resume_twirl1_zz.py --output results_cuprate_2d/lmpf_3x3_twirl1_zz_completed_2026-09-09_v1
timeout --signal=KILL 120s env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /home/bram/.venvs/qiskit/bin/python -B lmpf_2d/verify_resumed_twirl1_zz.py results_cuprate_2d/lmpf_3x3_twirl1_zz_completed_2026-09-09_v1
timeout --signal=KILL 120s env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /home/bram/.venvs/qiskit/bin/python -B lmpf_2d/portable_archive.py pack results_cuprate_2d/lmpf_3x3_twirl1_zz_completed_2026-09-09_v1
```

Actual output (selected fields; full JSON retained):

```text
TESTS_PASSED 75
REUSED_STATES_VERIFIED 7
MISSING_STATE_DONE 133.949
TWIRL1_ZZ_RESUMPTION_COMPLETE
raw_full_gram_relative_change: 0.013129585436624893
exact_norm_full_gram_relative_change: 0.0017990859443744063
G_relative_change: 0.0013511144510283126
b_relative_change: 0.005049922116133582
shot_aware_coefficient_l1_change: 0.018010897938295245
raw_flags_pass: false
exact_norm_local_flags_pass: true
new_states: 1
reused_states: 7
assembled_states: 8
seconds: 158.02153017099772
peak_rss_bytes: 491802624

RESUMED_TWIRL1_ZZ_RAW_TN_KKT_AUDIT_PASSED
reused_states_verified_byte_for_byte: 7
parent_timeout_preserved: true
assignment_matrix_penalty_verified: true
independent_overlaps: 20
independent_fits: 2
native_gates_checked: 20205
unique_native_unitaries: 62
maximum_native_unitarity_error: 2.220446049250313e-16
maximum_gram_error: 2.220446049250313e-15
maximum_weight_error: 4.440892098500626e-15
maximum_projected_gradient: 4.163336342344337e-17
maximum_objective_error: 2.7755575615628914e-15
maximum_stability_metric_error: 1.6237011735142914e-14
largest_contraction_intermediate_elements: 262144
largest_estimated_contraction_flops: 1562378384
raw_flags_pass: false
exact_norm_local_flags_pass: true
hardware_accuracy_validated: false
new_qpu_seconds: 0
seconds: 11.713403740002832

Archive status: PASS
selected_originals: 4
verified_objects: 4
restored: 0
already_present: 4
```

All three processes exited0. The prior process exited on its declared block
deadline; that failure is retained, not converted into success retroactively.
No source module from the parent calculation was modified.

## Independent checks and scope

All parent partial_manifest.json entries and numerical-source/input hashes were
verified before reuse. The seven copies are byte-identical, including NPZ,
tensor metadata and their generation records. New state count is exactly1.
Additional tests reject altered twirl/operator/chi/shot/guard/record settings
and reject overwrite or source-checksum mismatch during copying.

Production uses the unchanged canonical-chain kernel and left-to-right
environments. The audit contracts reversed raw bra/ket tensor networks with a
separate guarded contraction tree, and reconstructs both complete4x4 Grams.
Independent direct KKT systems replace the production null-space solver.
The joint readout penalty is verified by true-to-measured assignment inversion.

Raw Grams are PSD within the declared tolerance before exact-norm copies.
Chi256 raw/corrected minimum eigenvalues:
4.6216316801e-6 / 4.7633878428e-6.
All overlaps are dimensionless, Tr(A-dagger B)/2^18. For the ideal unitary
Pauli-string arm, F00=1 follows exactly without a target-state expectation.
Only that diagonal is changed; off-diagonal data and coefficients are retained.

The raw1% full-Gram criterion remains FAILED. The previously declared,
separate exact-norm F/G/b and coefficient criteria PASS. This distinction is
essential: we do not claim raw convergence, asymptotic certification, or that
the effective noise surrogate has been validated against the actual device.

No target bitstrings or target reference expectations were used for selection
or fitting. No clipping, retuning, zero-filled missing arm, product of separate
noisy Z operators, eight-twirl mixture, full-profile validation or6x6 escalation.

The completed numerical assembly enables a subsequent matched archived-hardware
robustness check. It is not itself evidence of improved hardware observables.
