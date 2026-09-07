# Focus: better 6x6 quantum data, not a harder classical benchmark

User correction 2026-09-07: improve quantum results. Classical time/U scans
and chi128 work are deferred, not the next automatic task. No new hardware
authorization; the earlier 15-second pilot authorization is consumed.

This step builds and verifies a more compact PARAMETERIZED TFLO family.
Keep 6x6,32 particles,U=8,t=1,t'=-0.25,T=0.4,two steps and the original full
fermionic network. Retain U=0 training/holdout capability; never recompile
after binding. Same ideal family and physical layout as the completed pilot.

The older 72-us circuit was bound to one setting. Its performance cannot be
silently assigned to a new parameterized family. Start from the preserved
parameterized72_blocks.qpy of the completed TFLO/DD job, not a new slow global
transpile. Reference native base has20,736CZ; the old bound family had15,400CZ.

Exact transformations, to numerical synthesis tolerance:
1. Merge only constant one-qubit segments between CZ and symbolic-RZ anchors.
   Synthesize each distinct2x2 segment into native RZ/SX/X, retain its phase.
2. Cancel CZ pairs only through RZ/CZ operations (all diagonal and commuting)
   on their endpoints. Any non-diagonal endpoint operation breaks eligibility.
   Record every removed pair and independently verify intervening operations.
3. At most three cleanup/cancellation rounds; no routing/model/time changes.
4. Twirl the final parameterized circuit with the four original fixed seeds;
   compact only constant one-qubit segments once more BEFORE binding.
   Retain readout masks and logical-to-physical mapping. No ZNE-fold removal.

No DD is inserted in this offline candidate step. The earlier DD experiment
showed no significant benefit; if later included, it must be explicitly
scheduled and tested again. No live timing/ISA check or hardware error claim.

Equation and invariant registry:
- Constant block U=U_last...U_first; synthesize e^(i gamma)V=U, error<=1e-11.
- Global phase is affine in the original parameters. Accumulate constants
  with fsum; retain gradients exactly to double precision. Check sample binds.
- CZ^2=I; [CZ,RZ]=[CZ,CZ]=0. No cancellation across X/SX/measurement/barrier.
- Full72-mode one-qubit rewrite verification uses unchanged per-wire CZ and
  symbolic-RZ anchors,2x2 segment equivalence, and global phase accounting.
- Bound family retains exactly the same operation/wire skeleton at all six
  U0 training times, two U0 holdouts and U8 target. No ideal onsite term dropped.

Verification before candidate acceptance: native block operator checks,
parameterized small-system full-unitary and random-state checks at U=0/8 and
several T, valid/invalid CZ cancellations, measurement map, full72 structural
proofs, exact byte QPY roundtrip. Existing hardware and source archives immutable.

Metrics: compare original and optimized parameterized families with the SAME
four twirl seeds/layout/saved timing snapshot. Report CZ count/layers, physical
X+SX pulses, total depth and duration separately. Less CZ alone is not enough.
Snapshot durations are offline estimates, not live hardware times or job cost.
Before a submission: refresh backend/ISA, allocate shots/calibration/training,
verify budget and obtain new explicit permission.

Expected before run: merging constant rotations should reduce pulse overhead;
CZ cancellation gain is unknown. Do not assume the older bound72-us result is
reachable. A compact circuit can still be too noisy. TFLO holdouts must pass
on NEW data before calling observables restored. No parameter-driven clipping
or training on U8/MPS target answers.

Limits: CPU only, one numerical thread, worker600s,process630s,2GiB RSS checks.
No packages installed, no QPU/network calls, no longer-time evolution or chi128.
QPY originals retained locally; any file over10MB gets a verified lossless
gzip mirror for the local Git checkpoint rather than staging the large binary.

Method reference: https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.synthesis.OneQubitEulerDecomposer
Physics-skill: independent exactness checks, equal family/snapshot comparison,
resource boundaries, complete preservation and no premature hardware claims.
