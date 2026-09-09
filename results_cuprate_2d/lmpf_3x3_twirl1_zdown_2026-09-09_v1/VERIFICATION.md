# Verification: matched twirl1 central Z_down

Status: independent audit PASSED; all predefined local chi gates PASSED;
hardware accuracy NOT EVALUATED and NOT VALIDATED.

## Executed independent numerical check (Level 5)

Environment: WSL Ubuntu-Preview-C, /home/bram/.venvs/qiskit/bin/python;
OPENBLAS_NUM_THREADS=1, OMP_NUM_THREADS=1, threadpool_limits(1).
Dependency versions and SHA256 provenance are recorded in plan.json.

Actual commands, executed from repository root:

```bash
timeout --signal=KILL 600s env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /home/bram/.venvs/qiskit/bin/python -B lmpf_2d/twirl1_zdown.py --output results_cuprate_2d/lmpf_3x3_twirl1_zdown_2026-09-09_v1
timeout --signal=KILL 120s env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /home/bram/.venvs/qiskit/bin/python -B lmpf_2d/verify_twirl1_zdown.py results_cuprate_2d/lmpf_3x3_twirl1_zdown_2026-09-09_v1
```

Actual output (selected fields; full JSON and tests.txt retained):

```text
TESTS_PASSED 67
TWIRL1_ZDOWN_OPERATOR_CHECK_FINISHED
new_states: 8
raw_full_gram_relative_change: 0.002971349938259023
exact_norm_full_gram_relative_change: 0.0007857569239514819
G_relative_change: 0.0002330301525492284
b_relative_change: 0.0012017461951425014
shot_aware_coefficient_l1_change: 0.008342765004701547
raw_flags_pass: true
exact_norm_local_flags_pass: true
seconds: 54.35050610300095
peak_rss_bytes: 397201408

TWIRL1_ZDOWN_RAW_TN_KKT_AUDIT_PASSED
observable: 9
central_calibration_mode_index: 1
independent_overlaps: 20
independent_fits: 2
native_gates_checked: 20205
unique_native_unitaries: 62
maximum_native_unitarity_error: 2.220446049250313e-16
maximum_gram_error: 1.1102230246251565e-15
maximum_weight_error: 7.271960811294775e-15
maximum_projected_gradient: 5.551115123125783e-17
maximum_objective_error: 1.7763568394002505e-15
maximum_stability_metric_error: 2.609024107869118e-15
largest_contraction_intermediate_elements: 65536
largest_estimated_contraction_flops: 179122064
all_source_input_output_hashes_verified: true
hardware_accuracy_validated: false
new_qpu_seconds: 0
seconds: 3.6226857299989206
```

Both processes exited0. All eight state roundtrips preserve their norms.

## Independent algorithms and mode selection

Production uses the unchanged canonical-chain kernel and exact left-to-right
MPS overlap environments. Audit uses raw bra/ket tensors, reversed ordering and
a separately generated resource-guarded contraction tree. All20 entries are
recomputed, not one representative pair. No dense18-qubit superoperator.

Production coefficients use the existing null-space constrained solver.
Audit solves direct4x4 KKT systems and independently recomputes stationarity,
sum(c)=1, objective components and convergence decisions.

Z_down is mode9/physical108 and calibration column1 in central ordering(8,9).
The audit hard-checks the mode, support, physical layout, masks and the
closed-form penalty 1/[(1-e0_down-e1_down)^2*N_a].
New tests perturb the two calibration columns independently, interchange them,
vary masks, and reject invalid calibration inputs. This detects a copied
Z_up-column error even though the real archived calibration values are equal.

## Mathematical and validation boundaries

Dimensionless normalized Hilbert-Schmidt overlaps Tr(A-dagger B)/2^18.
The unitary Pauli identity gives exact F00=1 independent of input state.
Raw Grams are validated before a separate F00-only correction; no G/b repair.
Chi128 raw and corrected minimum eigenvalues are2.5225108265e-5 and2.5384358979e-5.

The correction changes neither weights nor off-diagonal data. No clipping,
reference fitting, target scoring, hyperparameter scan, favorable seed choice
or reuse of Z_up/twirl0 operator states. The prior Z_up helper functions are
reused unchanged, which is code reuse, not operator-data reuse.

Passing a chi64/128 comparison for one operator is not an asymptotic error
certificate. The archived local gate-error depolarizing model is not a learned
or validated device channel. Readout-calibration uncertainty is not propagated
in this operator-only check and must be included in later hardware scoring.

No target bitstrings, target means or exact target expectations were used.
The ZZ operator, central three-observable hardware comparison, eight-twirl
mixture and6x6 extension remain outside this completed step.
