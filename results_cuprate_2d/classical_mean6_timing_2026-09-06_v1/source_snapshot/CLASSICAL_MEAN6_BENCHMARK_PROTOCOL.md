# Frozen scope: classical six-profile mean timing

Purpose: measure the already selected classical control, not discover or tune
a new predictor. No hardware calls, no new MPS run, no edits to old archives.
This baseline was selected after viewing the U=8 comparison; timing it does
not make it a prospectively validated solver of interacting dynamics.

Fixed inputs: 6x6, 4 holes, stripe-Neel, open boundaries, t=1, t'=-0.25,
mu=0, two palindromic network steps; hbar=1, mode order up/down per site.
Six U=0 finite-circuit times: 0.04,0.08,0.12,0.24,0.32,0.48.
Use the existing unmodified flo_reference and physical_observables functions.
Prediction: arithmetic mean of all six exact U=0 profiles, equal weights.
U=8 target data and stored training answers are NOT inputs to the predictor.

Equation registry:
- Orbital pair update: phi_p'=cos(theta)phi_p-i sin(theta)phi_q,
  phi_q'=cos(theta)phi_q-i sin(theta)phi_p; theta=c*T/(2*steps).
- C=Phi Phi^dagger, n_q=C_qq; charge=n_up+n_down, spin=n_up-n_down,
  doublon=n_up*n_down-|C_up,down|^2. Existing flo_reference computes these.
- Predicted site profile=(sum of six generated profiles)/6.
- RMS_j=sqrt(sum_sites((prediction-reference)_j^2)/36), evaluation only.
Physical evolution times are dimensionless hbar/t units; execution timers
are seconds, never conflated. Absolute observable errors are not percentages.

Expected before timing: N=32 to about 1e-12; RMS versus old chi64 approximately
[0.0293063,0.0575941,0.0113766]. Runtime not yet measured. 72x32 orbital
arrays and finite loops are small; no Hilbert-space statevector for 6x6.

Run five sequential fresh Python processes, one BLAS/OMP thread. Never flush
OS caches or change system power settings. Fresh process is not a disk-cold
machine. Report all runs, median and range, not only the fastest. Each worker
gets a 30-second timeout. PowerShell records full Windows->WSL->Python->JSON
return time. Worker separately records import time, compute-only time for all
six references plus averaging, and time to result-ready. No startup is silently
hidden; JSON formatting/output and termination belong to the outer timer.
No parallel benchmark runs; other machine load is uncontrolled and recorded.

Worker denies archive/credential file access and network connections before
imports. It reads no plan, saved references, MPS output, or hardware results.
The parent reads those only AFTER all timed worker processes have finished.
The benchmark includes recomputing every reference, not just averaging a cache.

Verification outside compute timer: each covariance is Hermitian, projector,
trace=32, separate spin counts=16; no up/down mixing. Pauli conversion is checked
against direct covariance observables. New predictions and each training row
must reproduce the old archive to 1e-12. Small 2x2 statevector, zero-time,
invalid-time and mean-linearity tests run before the timing repetitions.

No general dynamics accuracy certificate: fixed two-step U=0 references are
exact up to roundoff for that circuit, but their mean is only a heuristic for
the U=8 target. Chi64 is not a certified exact reference. No extrapolation in
system size, other U, or other time. Old MPS timing includes concurrent local
work; it is context, not a fresh isolated benchmark. QPU usage, service wall
time and total CPU workflow time remain separate columns.

Physics skill: explicit timing boundaries, independent checks, all repetitions,
source hashes, immutable old data, exact scoped local Git checkpoint. No push.
