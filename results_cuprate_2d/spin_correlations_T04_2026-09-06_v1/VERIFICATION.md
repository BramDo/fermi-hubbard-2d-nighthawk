# Verification of connected-spin extraction

This verifies implementation and extraction. It does NOT certify 6x6 chi64
accuracy, continuous-Hamiltonian dynamics, or any quantum-advantage claim.

Executed six-test suite before the worker (actual output in unit_tests.txt):

```
test_flo_wick_matches_full_quantum ... ok
test_mixture_includes_classical_covariance ... ok
test_product_state_zero_connected ... ok
test_random_mps_against_dense ... ok
test_safety_limits ... ok
test_shells_do_not_cancel_signed_errors ... ok
OK
```

Independent computational oracle, executed after the new extraction:

```
python -B -u verify_spin_correlation_probe.py
```

Actual output excerpt:

```json
{
  "status": "PASS",
  "exact_3x3_direct_site_probability_max_abs": 2.1649348980190553e-15,
  "six_by_six_Quimb_four_mode_operator_max_abs": 1.3322676295501878e-15,
  "total_covariance_mixture_identity_max_abs": 3.3306690738754696e-16,
  "old_inputs_sha256_verified": 28,
  "analysis_hashes_verified": 24
}
```

Small exact anchor: all-pair MPS RMS errors for chi16,32,64 are respectively
0.0172324, 0.00640143, 0.00125219. No assumed algebraic convergence order
in chi: these are observed errors against exact finite-circuit evolution.
The 6x6 chi32->64 screening fails, so no certified reference is claimed.

FLO uses Gaussian Wick moments including exchange. The six-time mixture is
formed by averaging first and second raw moments, then centering. Its extra
between-time classical covariance is retained. All site pairs are stored;
the signed-error average is not substituted for RMS or maximum pair error.

For a fixed-spin state, the connected matrix row sums should vanish. These
diagnostics, covariance positivity and onsite-variance identities are saved
for every result, without treating an MPS diagnostic as a truncation bound.
