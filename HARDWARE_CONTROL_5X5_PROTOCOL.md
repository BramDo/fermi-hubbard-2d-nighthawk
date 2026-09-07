# One hardware control job: 5x5 FLO and 5x5/6x6 preparation

User replied "Ja" to preparation and submission of ONE job, maximum5 QPU
seconds, only after a fresh hardware and budget preflight passes.
Backend ibm_phoenix, saved IBM account qiskit-runtime-q9. No Fire Opal.
No automatic retry, alternative backend, session or batch. The canonical
attempt marker survives failures and prevents duplicate submissions.

## Fixed scope, predictions and conventions

- 5x5:50 fermion modes,3 holes,22 particles (11up/11down), stripe-Neel,
  open boundaries, t=1,t-prime=-0.25,T=0.4,two symmetric steps.
- The ONLY dynamical hardware setting is U=0. Its finite circuit has an
  exact FLO reference. Continuous-time U=0 is calculated separately.
- Compile the parameterized network before binding U. Preserve exactly
  the same native gate-name/wire skeleton at U=0 and U=8. The U=8 companion
  is archived locally only; it MUST NOT occur in submitted PUBs.
- The 5x5 layout is the first50 wires of the old validated72-qubit path.
- 6x6 preparation-only control: original72 wires and32 particles,
  16up/16down. No hopping, interaction or FSWAP evolution in this control.
- Preparation controls should reproduce their full known occupation
  profiles and zero doublons, not just their total particle number.
- Native readout calibration errors should be much smaller than the
  previously observed3.77-particle excess. This is a prediction, not a
  presumed outcome. Dynamics may still show substantial hardware error.
- hbar=1; spin is n_up-n_down, not Sz/2. Little-endian spin-interleaved
  occupation bits; classical widths are50 or72 as explicitly recorded.

## Shot allocation

12 scalar PUBs,512 shots each,6144 shots total:

- Four72-bit calibration PUBs: all0/all1 at start and end.
- Two5x5 preparation PUBs: unflipped and complemented readout.
- Two6x6 preparation PUBs: unflipped and complemented readout.
- Four independent explicit Pauli/readout twirls of the5x5 U=0 circuit.

The eight target PUBs are shuffled once using a frozen seed. Circuit
ordering does not guarantee wall-clock drift resolution: provider shot
execution order is not assumed. Calibration blocks are nominal bookends.
No ZNE, PEC, qDRIFT, TFLO fitting or postselection. Raw and readout-corrected
results both remain visible. No clipping or forcing particle conservation.

## Budget and dispatch

- max_execution_time=5 in a single SamplerV2 job;512 shots per PUB.
- Initialization on; preserve the freshly reported backend default
  rep_delay. Built-in twirling/DD off; explicit twirls already included.
- Fresh ISA, faulty-qubit/gate, native timing, alignment, memory and quota
  checks before preflight AND immediately before the single POST.
- SDK duration and independent wire critical path must agree. Include
  initialization reset, measurements and rep_delay for every shot.
- Planning gate: two approximate2-second internal-subjob overheads plus
  shot execution must be <=4.75 seconds, leaving0.25 seconds headroom.
  This is a deliberately small12-PUB diagnostic, not the old26-PUB,
  three-folding-factor job. Also show1/2/3-subjob scenarios.
- Internal subjob count is unknown. Passing is not a promise of completion:
  if overhead exceeds the plan, the provider5-second cap may cancel the job.
- Reject explicitly reported remaining quota below5. Missing quota fields
  remain unknown; the explicit per-job5-second cap is the spending guard.
- Disable HTTP submission retries. Persist intent with fsync BEFORE POST,
  print and persist the job ID before any wait, and verify provider cap.
- Once attempted, recover by unique tag or retrieve that job only.

Sources: IBM workload usage and maximum execution time documentation,
checked2026-09-06. Hardware usage is not wall time; failed jobs can consume
budget. No old result, source, lock or permission is overwritten.

## Verification and fixed analysis

Unit tests: small-system exact FLO-vs-statevector, fixed U0/U8 skeleton,
preparation masks, independent asymmetric-readout inverse including onsite
correlations, record allocation, and exactly-once failure/confirmation gates.
Archive QPY inputs, source snapshots, seeds, hashes, references, preflight,
actual provider PUBs, raw result/bitstrings, status, options and usage.

Primary comparison: measured charge/spin/doublon profiles versus the exact
IDEAL FINITE-CIRCUIT reference. Report total number and separate spin counts.
Continuous-time Trotter error is not attributed to hardware.
Pooled independent asymmetric readout channels, Jeffreys estimates using
1024 shots per calibration state. Report start/end rates separately.
2000 whole-shot conditional bootstrap replicates plus shared calibration
draws. Report numerical intervals as conditional, not total error bounds;
drift, correlated SPAM and readout-model bias are not covered.

Provisional diagnostic screen, not an accuracy certificate:
readout-corrected RMS charge<=0.05, spin<=0.05,doublon<=0.03 and
absolute total-number deviation<=0.5. Freeze before measurements. Report
all metrics and failures; thresholds do not authorize further jobs.

No U8 hardware or further6x6 dynamics are authorized by this job.
