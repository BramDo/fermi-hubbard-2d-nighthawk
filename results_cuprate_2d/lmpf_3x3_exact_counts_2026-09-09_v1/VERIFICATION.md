# Executed verification: exact finite-count diagnostic

Status: EXACT_COUNTS_COMBINATORIAL_AND_SCIPY_AUDIT_PASSED.

The physics-verification workflow required a written equation registry,
analytic limits, independent numerical execution and separation of
conditional statistical compatibility from physical-model validation.

## Scope, provenance and numerical validity

- Original raw bitstrings, backend, job, twirl, masks and exposures checked.
- Frozen parent prediction and its independent verification checked.
- Source snapshots, result manifest and source-input SHA256 values checked.
- Full count-vector completeness/uniqueness, normalization, mean and covariance
  identities tested: E[C]=nq, Cov(C)=n(diag(q)-q q^T).
- Physical and measured probability distributions checked without clipping.
- Readout forward order checked independently with a Kronecker matrix.
- No hardware calls, model fitting, state propagation or ideal-reference fitting.
- Fixed readout and IID assumptions remain explicit and unvalidated here.

## Ten executed unit tests

The tests cover enumeration completeness (n7/14/64), uniform categorical ties,
the exact n2 uniform tail1/4, fair binary n7 tail1/8, deterministic and impossible
outcomes, label symmetry, SciPy masses/moments, zero-readout mask permutation,
an asymmetric-readout analytic result, and invalid-input rejection.

Actual stdout: EXACT_COUNT_TESTS_PASSED 10.
Full unittest output: tests.txt.

## Independent computation (Level 5)

Executed command in WSL Ubuntu-Preview-C:

```text
/usr/bin/timeout --signal=KILL 60s env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
/home/bram/.venvs/qiskit/bin/python -B lmpf_2d/verify_exact_counts.py
results_cuprate_2d/lmpf_3x3_exact_counts_2026-09-09_v1
```

Exit code0. Selected actual stdout fields; complete output is saved in
verification/verification.json:

```json
{
  "status": "EXACT_COUNTS_COMBINATORIAL_AND_SCIPY_AUDIT_PASSED",
  "primary_count_vectors_verified": 48705,
  "primary_tests_verified": 3,
  "secondary_tests_verified": 9,
  "source_input_and_output_hashes_verified": true,
  "original_bitstrings_and_fixed_readout_verified": true,
  "maximum_differences": {
    "mass": 4.274358644806853e-15,
    "deviance": 1.4210854715202004e-13,
    "p_value": 7.327471962526033e-15,
    "normalization": 4.440892098500626e-15,
    "scipy_mass": 6.106226635438361e-16
  },
  "new_qpu_seconds": 0,
  "noise_model_validated": false,
  "seconds": 1.918409686000814
}
```

Independent primary p-values: .7311315043112887, .2354398785990632,
.510461736110809. Independent factor2 ZZ p-value: .1319918947450567.

Production stars-and-bars enumeration is not used by the verifier's nested
loops. Production log-gamma PMF and vector deviance are not used by its
integer-combinatorial PMF and scalar-log statistic. SciPy provides a third
mass evaluation check. Neither verifier imports the production module.

A separate PowerShell evaluation of the four-term seven-shot polynomial
returned .131991894745057, with double-precision difference0 from the
saved production tail. See DELIVERY.md for the explicit expression.

These checks verify the finite-count computation, not the truth of the
assumed noise model or a causal explanation of the hardware errors.
