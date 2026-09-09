# Submission verification, not result validation

Status: LIVE PREFLIGHT PASSED, ONE JOB SUBMITTED, PROVIDER CAP VERIFIED.
Fresh hardware result verification remains pending.

The physics-verification and credential-safety workflows enforced immutable
native circuits, calibration-only analysis rules, secret-safe account use
and an exactly-once submission boundary.

## Executed local tests

Preparation output:

```json
{"status":"PREPARED_NOT_SUBMITTED","tag":"lmpf3x3-floor64-4371dac8c4754bd0","pubs":20,"shots":3072,"cap":5,"tests":10}
```

The fake-job receipt printed by the exactly-once UNIT TEST refers only to a
temporary local fixture. It is not an IBM job; the real job is identified below.

Analysis unit-test output:

```text
test_calibration_broadcast_preserves_point ... ok
test_floor_penalty_is_eight_times_original ... ok
test_independent_inverse_and_kkt ... ok
test_partial_or_wrong_roles_rejected ... ok
test_sixteen_pub_strata_keep_exposure ... ok
Ran5 tests in0.026s
OK
```

These tests do not count as analysis of fresh hardware data.

## Actual live and provider output (Level5)

```json
{
  "event":"LIVE_GATE_PASSED",
  "pubs":20,
  "shots":3072,
  "cap_seconds":5,
  "two_subjob_estimate":4.075249664,
  "retries_disabled":true
}
```

Actual receipt:

```json
{
  "job_id":"dago39b9k43c73adleeg",
  "backend":"ibm_phoenix",
  "tag":"lmpf3x3-floor64-4371dac8c4754bd0",
  "plan_sha256":"9282910c5a52ccf356f28e74ee656a6debb8c95ae521ff72dcec356bfff7dad9",
  "cap_seconds":5,
  "shots":3072,
  "pubs":20,
  "automatic_retry":false
}
```

Independent provider cap check:

```json
{
  "job_id":"dago39b9k43c73adleeg",
  "expected_cap_seconds":5,
  "provider_cost_field":5,
  "verified":true
}
```

Actual final usage, returned shots, provider circuit/result metadata and
scientific accuracy are not yet available in this submission-stage record.
See status_history.jsonl for observations and running_metrics_snapshot.json
for the null usage/finish fields. This document is kept as historical evidence.
