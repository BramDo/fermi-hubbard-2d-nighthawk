# Connected-spin research continuation

USER PRIORITY UPDATE2026-09-07: the user redirected work to better QUANTUM
results. The longer classical scan and chi128 proposal below are DEFERRED.
See QUANTUM_RESULT_6X6_STATE.md for the current task. Do not auto-start them.

Current state: proposal and first bounded T=0.4 probe COMPLETE.
Proposal: ONDERZOEKSVOORSTEL_SPINCORRELATIES_2D.md (frozen in probe manifest).
Results: results_cuprate_2d/spin_correlations_T04_2026-09-06_v1/RAPPORT.md.

Completed: six tests; all pairwise connected-spin moments for saved 3x3
chi16/32/64 and 6x6 chi32/64; new exact 3x3 finite-circuit anchor; U0 instant
and correctly mixed six-time controls; independent site-probability and
Quimb checks. Worker18.865s; zero new QPU seconds. No process remains active.

Result gate: U0 mixture differs substantially in connected correlations;
6x6 chi32->64 reference screen FAILS. Do not certify chi64 or claim advantage.
3x3 chi64 connected RMS vs exact is0.001252, not a 6x6 error certificate.

Next proposed chunk: small exact3x3 time/U scan with dt refinement, then
selected6x6 chi128 convergence under a newly stated local time/RAM cap.
Neither chunk has run. Do not change the frozen proposal, raw data or hashes;
use a new result directory for follow-up work. Hardware authorization from
earlier pilots is consumed. No new submission without new permission.
