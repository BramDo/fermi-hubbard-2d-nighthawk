# Verification: matching twirl1 central hardware reanalysis

Status: independent numerical/analysis audit PASSED; robust hardware improvement
NOT ESTABLISHED;6x6 escalation NOT SUPPORTED by this result.

## Executed independent oracle (Level 5)

Environment: Ubuntu-Preview-C, /home/bram/.venvs/qiskit/bin/python,
OPENBLAS_NUM_THREADS=1,OMP_NUM_THREADS=1,threadpool_limits(1).
No provider session, new QPU, remote retrieval or new tensor propagation.

```bash
timeout --signal=KILL 120s env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /home/bram/.venvs/qiskit/bin/python -B lmpf_2d/twirl1_hardware.py --output results_cuprate_2d/lmpf_3x3_twirl1_hardware_2026-09-09_v1
timeout --signal=KILL 120s env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /home/bram/.venvs/qiskit/bin/python -B lmpf_2d/verify_twirl1_hardware.py results_cuprate_2d/lmpf_3x3_twirl1_hardware_2026-09-09_v1
```

Actual output (selected fields; full results saved):

```text
TESTS_PASSED 79
MATCHING_WEIGHTS_FROZEN_BEFORE_TARGET_SCORING
CENTRAL_TWIRL1_MATCHED_HARDWARE_REANALYSIS
operator_input_verification_seconds: 20.11936958899969
analysis_seconds: 1.3139773900002183
seconds: 26.264089084997977
new_qpu_seconds: 0
new_tn_states: 0

TWIRL1_HARDWARE_ASSIGNMENT_KKT_AUDIT_PASSED
methods_checked: 4
bootstrap_replicates_replayed: 10000
operator_sources_verified: 3
maximum_point_weight_error: 6.661338147750939e-16
maximum_penalties_error: 2.220446049250313e-16
maximum_weights_error: 1.7763568394002505e-15
maximum_pauli_error: 1.7763568394002505e-15
maximum_physical_error: 1.1102230246251565e-15
maximum_physical_fixed_calibration_error: 9.159339953157541e-16
maximum_physical_frozen_weights_error: 1.1379786002407855e-15
matched_shot_budget_verified: true
calibration_dependent_weights_verified: true
paired_intervals_verified: true
no_clipping_verified: true
hardware_accuracy_validated: false
seconds: 3.0558865450002486
```

Both processes exited0. Four added tests validate the matched baselines against
independent assignment inversion, batch/calibration-dependent coefficient
application, budget/mask rejection and preservation of unphysical estimates.

## Independent reconstruction

Production uses per-bit corrected score tables and a null-space constrained
optimizer. The audit solves full two-bit assignment inverses and direct KKT
systems. It reconstructs physical values through occupation probabilities,
rather than reusing the production affine transform.

Every saved calibration draw, target-stratum draw, penalty matrix, coefficient
vector, Pauli moment and physical output was checked. Fixed-calibration and
frozen-point-weight uncertainty variants were checked separately. Both paired
baseline-minus-LMPF error distributions and all summary intervals were replayed.

All source/input/output hashes are validated, including operator plans,
Grams and their independent audits, matching native QPY indices and bitstrings.
The three operators share the same job, layout, masks, calibration and native
channels. Their weights are frozen before target/reference scoring. The raw
ZZ stability failure remains recorded.

The16 possible entries of each calibration assignment matrix use
A[true,measured]. Readout inversion precedes unmasking. The fixed-order43/21
factor1 split preserves pairing with the64-shot baseline; the7/14 folded
strata are not merged or silently enlarged.

## What the data do and do not show

L-MPF point values:
charge0.41319210051669875, spin-0.13300019337150404,
doublon0.12555594614112828.

Exact finite-circuit reference:
charge0.4046706253064062, spin-0.3620211851492071,
doublon0.009685423195790493.

Point absolute errors are smaller than ZNE in all three components, and smaller
than readout-only in charge/spin but larger in doublons. ALL SIX paired
heuristic95% error-improvement intervals include zero. No robust general
improvement is established by this sample.

The L-MPF point joint probabilities are all positive, minimum0.014540007431469076,
without clipping. That is not proof of a faithful quantum state or low error:
doublons remain far above the exact point reference, and the bootstrap includes
negative estimates. Earlier failed/unphysical twirl0 results are untouched.

The uncertainty accounts for paired target sampling and shared Jeffreys
readout-calibration draws, with weight changes induced only by calibration.
It does not certify coverage at7 shots, include missing probability support,
or bound TN/model/coherent/correlated/drift errors. Intervals containing the
reference because they are wide are not evidence of matched accuracy.

Only one central site and one reused twirl are evaluated. Neither total N,
the full3x3 profile, an eight-twirl mitigation result,6x6 nor timing advantage
is validated. No additional control constraint or reference fit was applied.
