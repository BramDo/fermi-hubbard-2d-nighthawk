# Authorized3x3 floor64 job submitted; results pending

This is an immutable submission-stage record, not a completed-results report.

Job: dago39b9k43c73adleeg
Backend: ibm_phoenix
Created by provider:2026-09-09T15:56:21.226196Z
Provider running timestamp:2026-09-09T15:56:22.132917Z
Last status stored at this handoff: RUNNING.
The running metrics snapshot reports finished=null, usage=null and
circuits_execution_time_ns=null. Missing usage is UNKNOWN, not zero.

Exactly one job was submitted after the user's explicit Ja to512 shots per
factor,3072 total shots and a5 QPU-second maximum, following a passing live
preflight. The provider job metadata independently confirms cost=5, the
configured maximum execution time. This is a limit, not reported actual usage
and not a promise that cloud turnaround takes five seconds.

## Frozen experiment

Twenty PUBs:
- pre/post readout all0/all1,128 each:512 calibration shots;
- four blocks with shared factor1=128, factor2=128,
  baseline-only factor1=256 and factor3=128.

Totals: factor1=1536, factor2=512, factor3=512;3072 overall.
Main corrected methods each use1536 target shots plus512 calibration.
The512 shared factor1 shots are fixed by role, not selected from outcomes.

Same original3x3 native circuits and manual twirl1,18 active modes,N8,U8,
T=.4 and two symmetric steps. Runtime twirling and DD disabled, init enabled,
rep_delay=1us. This is a transfer test of archived operator Grams.
No new TN states, target training or exact-reference fitting were performed.

## Gates passed before dispatch

- Named saved IBM account qiskit-runtime-q9 ready; token and full instance
  identifiers are not copied or printed. Fire Opal is not used.
- Ten offline safety tests pass: exactly-once/uncertain-send locks, quota,
  options, unchanged record order, circuit signatures and raw archive mapping.
- Twenty QPY roundtrips preserve physics and measurement mappings.
- Live ISA/fault/backend/rep-delay checks pass for all20 PUBs.
- Fresh manual and SDK timing agree: .075249664s estimated shot execution;
  one/two/three internal-subjob scenarios2.07525/4.07525/6.07525s.
  Internal subdivision is unknown, so completion inside5s is not guaranteed.
- IBM usage endpoint reported56 consumed seconds but no remaining quota.
  Remaining quota is unknown, not treated as unlimited.
- All discovered runtime HTTP sessions had automatic retries disabled before
  the only Sampler POST. Canonical attempt marker remains in place.
- Grams, masks, floor64/eta1 rule and bootstrap contract were frozen before
  dispatch in analysis_inputs.json and analysis_contract_sha256.json.
- Provider max-execution cap verified after dispatch:5.

## Recovery boundary

Canonical attempt marker:
../hardware_lmpf_floor64_3x3_2026-09-09_attempt.json

Never remove it or submit again. Use only the existing receipt/job ID.
A pre-dispatch checkpoint is f013860. No Git push or publication occurred.

## Analysis ready, not yet executed on hardware data

The predeclared comparison covers raw, readout-only, linear ZNE,
original1/n L-MPF and floor64 L-MPF. Central charge/spin/D, physical
probabilities and paired absolute-error intervals will all be retained.
It uses10000 paired stratified bootstrap draws, seed2026090922, shared
calibration and calibration-dependent weights; no clipping or old/new
target pooling.

The analysis implementation was written and tested after dispatch, before
retrieval/scoring of new targets, and implements the already frozen contract.
Five synthetic analysis tests pass, including an independent assignment
inverse and KKT comparison. Actual hardware analysis and its independent
10000-draw audit are PENDING. No mitigation improvement is claimed yet.

Next commands, using the existing WSL Qiskit environment:

```bash
python -B lmpf_2d/floor_hardware.py retrieve
# Only after DONE_ARCHIVED_VERIFIED:
python -B lmpf_2d/analyze_floor_hardware.py
python -B lmpf_2d/verify_floor_hardware_analysis.py results_cuprate_2d/hardware_lmpf_floor64_3x3_2026-09-09_v1/analysis
```

Retain any failure or negative result. No repeat, budget increase or6x6
extension is authorized by this submission.
