# Exact ideal-norm verification

Executed in the existing WSL Qiskit environment:
```sh
python -B lmpf_2d/norm_control.py --output results_cuprate_2d/lmpf_3x3_exact_norm_2026-09-09_v1
python -B lmpf_2d/verify_norm_control.py results_cuprate_2d/lmpf_3x3_exact_norm_2026-09-09_v1
```

Selected actual computation output:
```text
exact_normalized_trace: 1
sympy_version: 1.13.1
tests_passed: 40
all_followup_local_flags_pass: true
all_coefficients_unchanged: true
new_hardware_estimates: false
full_profile_or_8_twirl_validation: false
noise_model_validated: false
new_qpu_seconds: 0
seconds: 4.677096223000262
```

The symbolic example uses a complex unitary and an exact rational rotation,
not floating-point normalization. The separate archived-circuit check covered
20,109 native gates (57 unique matrices), with maximum unitarity deviation
2.220446049250313e-16. It does not test physical noisy channels.

Actual independent audit:
```text
status: EXACT_NORM_SAVED_EVIDENCE_VERIFIED
fits_checked: 12
maximum_direct_KKT_coefficient_error: 8.597567102697212e-13
maximum_before_after_weight_change: 0.0
maximum_residual_shift_error: 0.0
historical_raw_flags_preserved: true
followup_flags_pass: true
independent_hardware_validation: false
seconds: 0.5035926370001107
```

The verifier does not call the production fit or flag function. It solves a
direct equality-constrained KKT system, checks immutable G/b and source/input
hashes, reconstructs residuals and both classifications. Unit tests also show
that fixing a large known norm cannot hide a >1% change in the small G block
under the new separate-block guard, and that invalid original Grams are rejected.

This is a retrospective follow-up using the same data. All original raw-Gram
flags are retained, including the failed ZZ flag. Passing the additional
local gate is not an independent experiment, a rigorous truncation/noise-model
certificate or an improved hardware result. The ideal ZZ expectation remains
nonmonotone and its chi256 absolute error is still worse than at chi128.
