# Authorized single-job 6x6 TFLO/DD pilot

User authorization: Ja to ONE new 6x6 pilot, hard max_execution_time=15
QPU seconds, ONLY after a fresh passing preflight. No retry, session, batch,
budget increase, or reuse of an earlier authorization. Backend ibm_phoenix
(Nighthawk), named saved account qiskit-runtime-q9. IBM SDK only; no Fire Opal.

## Fixed model and allocation

Use the same full 6x6 open t-t-prime-U model and initial stripe-Neel state
as the archived original 6x6 run: 72 spin-interleaved modes, four holes,
N_up=N_down=16, t=1, t-prime=-0.25, U=8, target T=0.4, two symmetric steps.
No hopping term, fermionic sign, interaction, site, or time step is dropped.
The target is the finite circuit, not exact exp(-i H T). spin=n_up-n_down;
charge=n_up+n_down; doublon=n_up*n_down; all dimensionless, time in hbar/t.

U=0 train times: 0.04, 0.08, 0.12, 0.24, 0.32, 0.48.
U=0 held-out controls: 0.20, 0.40. U=8 target: 0.40.
Each of these nine settings has DD off/on, four common explicit twirl
seeds, and 512 shots per PUB: 72 dynamics PUBs, 36864 shots.
Four 72-bit all0/all1 calibration PUBs at nominal start/end, 512 each.
Total 76 PUBs and 38912 shots; no automatic changes to the allocation.
Execution order inside provider subjobs is not guaranteed. Pair DD arms
in the saved randomized input order; all settings share twirl identities.

Compile one PARAMETERIZED native circuit before binding U or T, with the
existing verified network generator and full original physical path.
Add explicit CZ Pauli/readout twirls; schedule DD off/on templates before
binding. Each DD arm has exactly one native gate/timing skeleton per twirl
across all training, holdout, and target settings. Both arms have equal
original-gate starts and total scheduled duration for a given twirl.
No numeric cleanup after binding; differences from the earlier historical
compiler are recorded and not attributed causally to mitigation.

DD uses labeled native X-X echo pairs inserted only in idle windows on the
72 measured physical qubits. Both arms are ALAP scheduled, off with delays,
on with idle replacement by X-X. No added CZ, no unvalidated Y translation.
The ideal X-X product is identity. Verify every labeled insertion pair,
per-wire original operation order/parameters, timing, duration, and QPY
roundtrip. Small dense unitary tests independently check equivalence.
Runtime DD and runtime twirling OFF because these operations are explicit
in the submitted circuits. Do not describe that flag as absence of DD.

## Fixed analysis, frozen before submission

Primary pipeline: per-qubit asymmetric readout inversion, then per-Pauli
affine TFLO y=a*x+b fit ONLY on six U=0 training settings, separately for
each DD arm. Fixed ridge lambda=0.001 towards (a,b)=(1,0), no time predictor,
no MPS fitting, no clipping and NO postselection before readout inversion.
This small affine prototype is not the paper's entire mitigation stack.
Fit coefficients, conditioning, physical-bound violations and amplification
are saved. Do not optimize lambda or select filters on held-out/target data.

Holdout reference is exact polynomial FLO for the ideal finite U=0 circuit.
Provisional screening thresholds: RMS charge/spin <=0.05, doublon <=0.03
at BOTH held-out times, with the upper 95% bootstrap RMS estimate also
below threshold. This is not an error certificate or transfer guarantee.
If the screen fails, keep TFLO predictions as DIAGNOSTIC_UNVALIDATED;
do not promote them to recovered physical results.

Compare raw, readout, TFLO for DD off/on on identical site observables.
Compare U=8 with saved MPS chi=64 and report chi32-to-64 differences separately:
chi64 is not a certified reference. Mandatory classical-only comparators:
exact U=0 at T=0.4, time-only linear regression on exact training answers,
and each learned fit evaluated with its training-input mean instead of
target hardware input. Apparent agreement with MPS alone is insufficient.
Report raw particle-sector acceptance diagnostically without filtering.

Bootstrap 400 complete experiments: whole shots resampled within each PUB,
shared independent Beta draws of the two readout calibration channels,
refit six training settings on each draw. Fixed seed 202609061615. Conditional
on the four fixed twirls, not a random-twirl-population certificate. Intervals
exclude drift, correlated SPAM, transfer bias, Trotter and MPS error.
No PEC, ZNE, MESR or GPR in this job. ZNE would need additional noise factors.

## Budget and stop gates

Fresh backend operational status, selected qubits/gates, exact ISA, delays,
instruction-memory estimate, repetition delay and calibration durations.
Independent wire clock versus SDK duration for every PUB. Include explicit
DD, measurement, reset and default rep_delay. Planning gate: estimated shot
execution plus FOUR internal subjob overheads (8 s) <=14.25 s. Save scenarios
1..8 subjobs; subjob count and completion within cap are not guaranteed.
Actual max_execution_time stays 15 even if provider estimate differs.
Known remaining quota <15 rejects; missing quota stays unknown, not unlimited.
Final live recheck immediately before submission, exact timing fingerprint
must match the scheduling snapshot; if it changes, STOP before any POST.

Canonical exclusive attempt marker is outside the run directory, created
BEFORE the only Sampler.run call. Disable HTTP retries. On uncertain dispatch,
recover read-only by unique tag, never resubmit. Save receipt immediately.
Verify returned provider cap representation; on mismatch cancel THIS job
protectively and stop. Store actual provider inputs, options, metadata,
bitstrings, metrics, complete results, code copies, tests, and hashes.

## Sources

- https://arxiv.org/html/2510.26845v2 (TFLO and validation boundaries)
- https://quantum.cloud.ibm.com/docs/en/guides/dynamical-decoupling-pass-manager
- https://quantum.cloud.ibm.com/docs/en/guides/estimate-job-run-time
- https://quantum.cloud.ibm.com/docs/en/guides/max-execution-time

Physics and safe-API skills enforce verification, explicit scope and archival
boundaries. They do not supply new hardware authority beyond the user's Ja.

## Local compiler deviation, before any hardware attempt

The global native optimization exceeded the 900-second local preparation
bound; its verified owned CPU process was stopped with no plan or hardware
attempt yet present. Use exact two-qubit block synthesis of the SAME
parameterized network/event order. Each fSWAP/hopping/onsite block is verified
as a full two-qubit unitary; random full 2x2 state tests include diagonal
hopping and interactions. The finite algorithm and all settings stay fixed.
Gate counts may rise: retain them honestly, and reject if fresh timing fails
the unchanged 15-second job gate. This is a compiler workaround, not qDRIFT,
term dropping, or a new approximation. Keep the failed local run log.
