# TFLO/DD 6x6 completed hardware and analysis checkpoint

FINAL STATUS (supersedes historical preparation notes below):
Job daesvo51ierc738mji3g DONE; 8 QPU seconds charged, cap15 confirmed.
76 provider circuits verified; 38912 shots archived. Retrieval session27187
and fixed analysis session16548 finished successfully. Both TFLO holdout
screens FAIL; negative onsite probabilities; no added U8 hardware-input value.
No demonstrated DD benefit or quantum advantage. DELIVERY.md and the independent
delivery_audit.json contain the final conclusions. Packaging is COMPLETE:
379 delivery hashes verified, 161 lossless QPY mirrors (1,885,665,704 original
bytes; 84,477,393 gzip bytes). Original QPY files remain untouched.
No further physics work is pending. NEVER submit another job under the consumed
authorization. This completed state and exact artifacts enter the local Git checkpoint.

Historical execution notes (not commands to repeat):

checkpoint_id: tflo-dd6-local-compiler-20260906
checkpoint_type: progress-save
checkpoint_reason: context_pressure
awaiting: none; hardware, analysis and archival verification complete
verification_prework_done: 15 new unit tests, 20 physics regressions, full
  synthetic analysis with 76 PUBs and 38912 shots passed. Source checkpoint
  a526c41. No hardware call or canonical submission attempt exists yet.
resume_contract: preserve all old archives and user changes; exactly one
  approved job with max_execution_time=15 ONLY after fresh budget pass.
success_path: block compile and tests -> prepare -> freeze/audit -> preflight
  -> one submit -> retrieve -> fixed analysis -> verification/archive.
issue_path: no submission if physics/ISA/timing/budget checks fail; never
  retry an uncertain POST; recover only by saved unique tag/receipt.

execution_segment:
  current_cursor: hardware, retrieval and fixed analysis COMPLETE
  completed_tasks: protocol, guarded runner, affine TFLO analysis, 16 tests,
    20 existing regressions, synthetic analysis, exact blockwise full72 compile
  current_task: completed; preserve sealed archive and consumed attempt marker
  resume_preconditions: inspect current files/logs; original global compiler
    pid14975 was verified and stopped after exceeding900s. No process from
    that attempt is running. Do not restart the expensive global compile.
    Native block compilation finished in26.3s:20736CZ, depth3005,
    full cell-unitary discrepancy2.88e-14. Source checkpoint5429c68.
    All4 DD pairs are verified: twirl0:4302pairs,120.212us;
    twirl1:4287pairs,121.012us; twirl2:4178pairs,120.372us;
    twirl3:4283pairs,120.612us. Plan and source snapshot ALREADY EXIST.
    Original prepare session36100 was stopped before sealing the bundle:
    generic circuit equality was too slow. Frozen intent and old sources
    were NOT modified. Resume session59840 COMPLETED at20:17:37UTC.
    All76 bound files and frozen_inputs_sha256.json exist and verify.
    Original full preflight session99229 COMPLETED: PASS at20:30:48UTC.
    Shot execution4.570226688s; four-subjob estimate12.570226688s;
    five-subjob14.570226688s; six would exceed15. Count unknown.
    Quota reports consumed41s but no remaining allocation, not unlimited.
    Final fresh checks PASSED at20:36:08UTC, including all120 fault flags
    clear, identical timing/options/instance, same12.57s planning result.
    One authorized attempt is ACTIVE in session3418 via
    submit_verified_tflo_dd6.py --confirm-one-job-max-15s.
    The canonical marker is created before SDK run. DO NOT invoke submit
    again, even if the receipt is not present yet. Wait for the session.
    Gzip preparation mirrors85/85 are complete and losslessly verified.
  first_result_gate_pending: false
  pre_fanout_review_pending: false
  pre_fanout_review_cleared: not_applicable
  skeptical_requestioning_required: false
  downstream_locked: true_until_fresh_preflight_pass

Root: C:/Users/Lenna/SynologyDrive/qlab/fermi-hubbard-2d-cuprate.
Run: results_cuprate_2d/hardware_tflo_dd6_2026-09-06_v1.
Lock: results_cuprate_2d/hardware_tflo_dd6_2026-09-06_attempt.json.
Runtime: Ubuntu-Preview-C, /home/bram/.venvs/qiskit/bin/python -B,
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 RAYON_NUM_THREADS=1.
Backend ibm_phoenix, 120-qubit Nighthawk, qiskit-runtime-q9 saved account.
Default rep_delay1us, dt4ns in latest read-only snapshot; recheck live.

Model and allocation are fixed in TFLO_DD_6X6_PROTOCOL.md. 76 PUBs,
38912 shots; 6 U0 train, 2 U0 holdout, 1 U8 target; DD off/on x4 twirls
x512 shots plus4 calibrations. No ZNE/PEC/postselection. Explicit native
XX DD means runtime DD flag stays OFF. TFLO has no time predictor and
must pass independent holdout screen; chi64 remains uncertified.

Current verified result: job daesvo51ierc738mji3g DONE, provider charged
8 QPU seconds within the confirmed 15-second cap. Created20:41:05UTC,
finished20:45:26UTC. Receipt and cap are saved. One attempt CONSUMED.
Retrieval session27187 started20:48:20UTC via tflo_dd6_fast_io.py retrieve;
provider circuit0 verified20:50:41UTC. Await it, do not duplicate retrieval.
After retrieval run analyze_tflo_dd6.py, inspect holdouts/independent checks,
write final delivery report, package_tflo_dd6.py and checkpoint exact artifacts.
Do not submit or change the frozen analysis/model/source files.

Historical submission instructions (already completed): read job_receipt.json and
provider_cap_verification.json. On an uncertain error use ONLY read-only
run_tflo_dd6_once.py recover by the unique saved tag; never retry POST.
Native compiler and tests are already complete. Do not redo or overwrite.
Fast I/O tests passed (byte roundtrip and rejection of changed gates,
phase and metadata). Retrieval should use tflo_dd6_fast_io.py retrieve,
not the slower original retrieve implementation. This helper NEVER submits.
Submission already STARTED; this is a description, NOT a command to repeat.
submit_verified_tflo_dd6.py reloads identical
hashed input bytes, verifies unchanged SDK/source, fetches fresh backend
status, all120 fault flags, timing/topology fingerprint, options, quota,
and recomputes budget. It reuses the completed full native scan ONLY when
inputs and target are identical; no guard is silently dropped. Eight mocked
submission-guard tests passed. This avoids repeating a15min deterministic
scan. It delegates the same exclusive dispatch_once and cap verification.
The dispatch_live_check now EXISTS; new invocations must block.
If marker exists, use recover/retrieve; never delete it to rerun.

Scheduled PARAMETERIZED QPY files are12-13MB each. Preserve them on disk;
the physics skill forbids staging individual binaries>10MB without approval.
For a complete Git backup, make lossless per-file gzip mirrors, verify their
decompressed SHA256 against original QPY, stage compressed mirrors (if<10MB)
and all small metadata/source files. Do not delete original frozen inputs or
change their filenames/hashes. Plain originals remain available to the runner.

This checkpoint records the context-pressure transition required by the
physics skill. No physics redirection or budget increase is authorized.
