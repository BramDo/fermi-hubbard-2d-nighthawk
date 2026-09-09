# Verification: matched twirl1 central Z_up

Status: independent saved-state audit PASSED; local chi gates PASSED;
hardware-accuracy gate NOT EVALUATED and NOT VALIDATED.

## Level 5: executed independent numerical oracle

Environment: WSL Ubuntu-Preview-C, /home/bram/.venvs/qiskit/bin/python.
OPENBLAS_NUM_THREADS=1, OMP_NUM_THREADS=1, threadpool_limits(1).
Versions and input/source SHA256 values are in plan.json.

Actual executed commands from repository root:

```bash
timeout --signal=KILL 600s env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /home/bram/.venvs/qiskit/bin/python -B lmpf_2d/twirl1_zup.py --output results_cuprate_2d/lmpf_3x3_twirl1_zup_2026-09-09_v1
timeout --signal=KILL 120s env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /home/bram/.venvs/qiskit/bin/python -B lmpf_2d/verify_twirl1_zup.py results_cuprate_2d/lmpf_3x3_twirl1_zup_2026-09-09_v1
```

Executed output (selected fields; complete results retained as JSON):

```text
TESTS_PASSED 63
TWIRL1_ZUP_OPERATOR_CHECK_FINISHED
new_states: 8
raw_full_gram_relative_change: 0.0036742052648007805
exact_norm_full_gram_relative_change: 0.0008583861306466491
G_relative_change: 0.0004016771655374666
b_relative_change: 0.0015840092111000289
shot_aware_coefficient_l1_change: 0.007181433657691916
raw_flags_pass: true
exact_norm_local_flags_pass: true
seconds: 50.02315717300007
peak_rss_bytes: 404275200

TWIRL1_ZUP_RAW_TN_KKT_AUDIT_PASSED
independent_overlaps: 20
independent_fits: 2
native_gates_checked: 20205
unique_native_unitaries: 62
maximum_native_unitarity_error: 2.220446049250313e-16
maximum_gram_error: 6.661338147750939e-16
maximum_weight_error: 4.884981308350689e-15
maximum_projected_gradient: 8.326672684688674e-17
maximum_objective_error: 3.552713678800501e-15
maximum_stability_metric_error: 1.8457457784393227e-14
largest_contraction_intermediate_elements: 65536
largest_estimated_contraction_flops: 179693456
all_source_input_output_hashes_verified: true
hardware_accuracy_validated: false
new_qpu_seconds: 0
seconds: 3.657088518997625
```

Both processes exited0. The numerical kernel is unchanged from earlier runs.
The deadline wrapper delegates exactly the same channel matrix and only checks
the clock between blocks. Five new tests cover deadline delegation, closed-form
Z_up shot variance, mask invariance, F00-only correction, direct KKT agreement,
missing levels, invalid Gram matrices and ill-conditioned readout rejection.

## Independent method and mathematical checks

Production: explicit left-to-right chain environments.
Audit: raw bra/ket tensor network, reversed tensor ordering, greedy contraction
tree guarded before execution. No chi-fourth-power local bra/ket preprocessing.
All twenty independent Gram entries are recomputed, not just one spot check.

Production fit: null-space constrained solver.
Audit fit: direct 4x4 KKT linear system. Sum(c)=1, stationarity and both
objective components are re-evaluated. The Z_up penalty is independently
reconstructed as 1/[(1-e0-e1)^2*N_a]; masks cannot change its outcome range.

All operator overlaps are dimensionless in Tr(A-dagger B)/2^18 normalization.
The exact unitary-Pauli identity gives F00=1, independently of any target state.
Original Grams are checked before the correction. At chi128, raw/exact-norm
minimum eigenvalues are4.8477043291e-6 and4.9086531793e-6. No PSD repair,
clipping, surrogate-rate fit, target-state fitting or favorable seed choice.

## Limits

Convergence evidence is one chi64/128 comparison for one operator and one
twirl, conditional on the specified approximation. It is not an asymptotic
error certificate or independent validation of the device's noise model.
The exact F00 identity cannot bound unmodelled coherent/correlated noise.

No target bitstrings, target means or exact target expectations were used.
Only readout calibration fields from the previously hash-verified frozen-rule
artifact were reused, never its twirl0 states, overlaps or weights.
Coefficient uncertainty due to calibration is not propagated in this
operator-only diagnostic; a subsequent hardware comparison must propagate it.

All historical failures and arrays remain. Z_down/ZZ, full central physical
observables, an eight-twirl mixture and6x6 are outside this completed step.
