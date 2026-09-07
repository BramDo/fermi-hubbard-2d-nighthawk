# Active direction: improve quantum results

UPDATE 2026-09-07: user authorized the proposed one-job original/compact
6x6 hardware test ("Laten we maar een hardware test 6 x6 doen"), max15 QPU
seconds. New run: results_cuprate_2d/hardware_compact_tflo_2026-09-07_v1.
Protocol: HARDWARE_COMPACT_TFLO_PROTOCOL.md. New independent attempt marker;
old authorization/lock remains consumed and untouched.
SUBMITTED at2026-09-07T07:29:39Z: job daf6foe42tqs73avhoeg on ibm_phoenix.
Provider cost/max cap15s independently confirmed. All76PUBs,38912shots;
fresh preflight estimate11.905900544s for four assumed internal subjobs.
New authorization is now CONSUMED. Retrieve by ID; never resubmit.
DONE confirmed: provider metrics usage.qpu_charge_time_seconds=7, status=complete.
Provider running07:29:40.172356Z -> finished07:32:41.030678Z (~181s).
This is7QPU-seconds, not7seconds end-to-end. Full input/result retrieval
and quality analysis are COMPLETE. All76 provider circuits and38912 shots
match;19tests and independent bit/RMS/fit/readout checks pass.
RESULT: no demonstrated quality improvement. Both original/compact TFLO
holdout screens FAIL. U8 readout+TFLO RMS charge/spin/doublon:
original .083889/.091851/.050805; compact .109304/.125864/.064116.
These are point discrepancies versus uncertified chi64; all paired U8 TFLO
gain intervals include zero. No-target-hardware null remains better.
Exact U0 T.4 TFLO spin RMS .390277 original/.358653 compact, far above .05.
Full interpretation: new run/CONCLUSIE.md and analysis/RAPPORT.md.
No new quantum advantage or restored6x6-dynamics claim. No further job
authorized. Final archive SEALED:376 file hashes verified,160 lossless QPY
mirrors verified, combined bootstrap byte-exactly recoverable from per-arm
mirrors. All original large files retained locally. No process remains except
the final local Git checkpoint at delivery; no automatic hardware follow-up.
Nighthawk ibm_phoenix active, no faults at initial check; existing q9 instance
is pay-as-you-go, so no remaining quota is claimed from its usage-only API.
Actual fresh timing: original123-124us, compact81-82us. Same20,736CZ.
Nineteen tests pass; analysis frozen before submission. Current hardware
submission/result state must be read from this new run's receipt and metrics.
The paragraphs below preserve the prior offline-only completion history.

User explicitly corrected the direction on2026-09-07: quantum result quality
is the goal. Classical time/U scans and chi128 work are DEFERRED, not the
next automatic action. The spin-correlation research is preserved as context.

Completed task: offline compact PARAMETERIZED TFLO family for the same full
6x6,U8,T0.4,two-step target. Start from the completed pilot's saved native
template, preserve original physics/layout, simplify before binding.
Protocol: QUANTUM_COMPACT_TFLO_PROTOCOL.md.
Output: results_cuprate_2d/quantum_compact_tflo_2026-09-07_v1.

Allowed this step: local implementation, tests, circuit preparation and
saved-calibration comparisons. No hardware job or live credentials needed.
Earlier15-second authorization is consumed; any new job needs fresh budget,
ISA checks and explicit user permission. No automatic submit/retry.

Old bound72-us candidate is NOT assumed to be a parameter-matched TFLO family.
Current work tests that possibility structurally, with independent checks.
No lower hardware error is claimed until a new controlled run validates it.

RESULT2026-09-07: build and verification COMPLETE. Four twirls shortened from
120.212-121.012us to80.252-80.452us in the same saved timing snapshot, about33%.
Physical X+SX pulses reduced about65%; CZ remains20,736 and584CZ layers.
All36 parameter bindings preserve structure. Six tests passed. Five actual
old provider circuits independently matched; four SDK clocks agree.
Report and proposed paired original/compact hardware pilot are in the new
output folder. The proposal is NOT authorized or submission-ready. No QPU
job or live backend query was made. No process remains running after delivery.
Next decision requires explicit permission for any new hardware job; suggested
cap15s is conditional on fresh budget/ISA checks. Never reuse the old approval.
