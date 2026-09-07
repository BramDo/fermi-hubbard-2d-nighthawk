# Verification of compact parameter-matched quantum circuits

Executed before full72 processing:

```
test_CZ_cancels_only_through_diagonal_endpoints ... ok
test_constant_full_operator_and_symbolic_anchors ... ok
test_full_small_network_family ... ok
test_measurement_mapping_preserved ... ok
test_twirl_cleanup_preserves_family ... ok
test_wrong_anchor_and_gate_rejected ... ok
Ran 6 tests in 9.540s
OK
```

Full-size structural checks are in native_rewrite_proof.json and the four
twirl*_constant_rewrite_proof.json files. No full72-qubit statevector claimed.
No CZ pairs were removed in the actual full-size run. Changes are1q-only.

Independent oracle command:

```
python -B -u verify_compact_symbolic_tflo.py
```

Actual output:

```json
{
  "status": "PASS",
  "provider_circuits": 5,
  "SDK_clock_checks": 4,
  "max_segment_error": 9.155133597044475e-16,
  "max_global_phase_error": 1.573520591756896e-11,
  "seconds": 44.96780845799367
}
```

The five comparisons use actual archived provider QPY files for U8 target
twirls0-3 and U0,T0.4 holdout twirl0, all DD-off. Only identity delays and
barriers are removed for the ideal-unitary comparison. Pauli/readout masks,
CZ partial order and classical bit mapping agree. This is stronger than
comparing only population in one initial state, but not an interval certificate.

All36 parameter bindings preserve the same pulse/gate/wire skeleton per
twirl. All five new QPY files have byte-exact roundtrips and verified lossless
gzip mirrors. SDK and independent integer clock agree for all four targets.
Timing is based on the archived calibration. No live backend, new data,
TFLO holdout success or hardware noise reduction is verified by these checks.
