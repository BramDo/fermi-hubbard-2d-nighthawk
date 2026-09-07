# Verification: classical six-profile timing

The implementation and timing checks passed. This does not certify the
post-hoc mean as an interacting U=8 solver or certify chi64 accuracy.

Executed before timing:

```
python -B -u test_classical_mean6.py -v
test_forbidden_inputs ... ok
test_full_small_quantum_circuit ... ok
test_invalid_time ... ok
test_linear_conversion_of_mean ... ok
test_network_forbidden ... ok
test_zero_time ... ok
Ran 6 tests in 0.111s
OK
```

Five fresh worker processes recomputed all six references. Actual analysis:

```json
{
  "training_profiles_match_archive_max_abs": 0.0,
  "historical_RMS_reproduced_max_abs": 0.0,
  "repeat_profile_max_abs": 0.0,
  "config_matches_frozen_plan": true,
  "all_references_recomputed": true,
  "comparison_loaded_after_timed_workers": true,
  "source_hashes_match_protocol_manifest": true
}
```

All covariance invariants were checked outside the compute timer and inside
the complete Windows-call timer. Their residuals are in each worker record.
No full 6x6 statevector, no stochastic sampling, no interaction approximation
silently passed off as exact: only the U=0 finite-circuit references are exact
up to roundoff. No step-refinement claim, since the target is the fixed circuit.

Independent standard-library verification repeats RMS calculations without
NumPy and recomputes all timing statistics from the five individual records.
It verifies source snapshots and the hashes of old input artifacts. Results
are in `independent_verification.json`; the whole new package is covered by
`delivery_sha256.json`. Existing archived experiments remain unchanged.
