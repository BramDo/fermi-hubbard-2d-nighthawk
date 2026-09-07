# Bounded classical 6x6 benchmark: full fermionic target, T=0.4

2026-09-06. User goal: beat this PC with a quantum computer for the SAME
observable task and acceptable accuracy. This stage measures the classical
baseline only: no hardware, network provider, submission or QPU spending.

## Target and algorithm

Full t-t'-U, open6x6 lattice,36 sites/72 spin modes,4 holes, stripe-Neel,
Nup=Ndown=16; t=1,t'=-0.25,U=8,mu=0,T=0.4,two symmetric network steps,dt=0.2.
Use exactly the parameterized_network product ordering underlying the3x3
hardware pilot. This is NOT the old number_preserving_t_only,T=0.1 circuit.
No claim of convergence to continuous-time Hamiltonian dynamics: the fixed
finite circuit is the common quantum/classical task.

Fuse each adjacent routing/hopping/onsite block into one exact4x4 matrix:
G=CP(-U*dt/2) [P(pi/2) tensor P(pi/2)] XXPlusYY(pi+c*dt).
For non-onsite pairs, the CP angle is zero. c is the actual spin-preserving
fermionic hopping coefficient, including t'. Pure routing is fermionic SWAP,
not bosonic SWAP. All10224 adjacent updates are retained in the same ordering.
This eliminates unneeded native-gate decomposition overhead for the classical
algorithm without changing its target unitary. No random data or noisy shots.

Quimb1.13 MPS, complex128, canonical-center tracking, dense SVD, relative
cutoff1e-10, no implicit SVD renormalization. Normalize at each layer using
the known canonical-center norm. Save the accumulated log retained norm as
a TRUNCATION DIAGNOSTIC, not a certified global error/fidelity bound.
Charge=nup+ndown, spin=nup-ndown, doublon=nup*ndown at ALL36 sites.
Report particle-number drift and all local observables; never clip/filter.

## Machine and limits

Host CPU verified: AMD Ryzen5 3500U,4 physical cores/8 logical threads,
14903533568 bytes RAM. Existing WSL exposes3 CPUs and about8GB RAM.
Use all3 available WSL CPUs for the main benchmark; no WSL settings change.
CPU only, no CUDA. This is not an optimized all8-host-thread benchmark.
Main profiles: chi8,16,32; separate fresh worker per profile, max180s kernel
and210s process wall limit, RSS guard2GiB. Stop higher-chi progression after
an incomplete/timed-out profile. Preserve partial progress; never present it
as a completed result. No automatic restart of a timed-out worker.
If chi32 completes, repeat that profile with1 BLAS thread as a fixed runtime
sensitivity check (same limits). Different thread runtimes must retain the
same converged observables to count as equivalent results.

## Validation and convergence screen

Before production: fused block versus Qiskit4x4 matrix; fermionic-SWAP sign;
exact2x2 state/observables at full bond16; U=0 FLO cross-check; norm and N.
Then3x3 chi16/32/64 against the archived exact27-moment reference at T=0.4,
max120s per kernel. Use these to expose errors in both implementation and
truncation. The3x3 exact reference is NEVER used to fit6x6 predictions.

The6x6 convergence screen requires BOTH chi8->16 and16->32 differences
to have spin-RMSE<=0.01 and max-site spin difference<=0.03, with charge and
doublon RMSE<=0.01 and total N within0.01 of32. Even a pass is heuristic
stability evidence, NOT a rigorous6x6 error bound or hardware accuracy target.
The user has not yet fixed the matched-accuracy tolerance for a speed claim.
Failure/timeout does not prove classical intractability or quantum advantage.

Report actual kernel timings (initialization, evolution, observables), cold
worker time including imports, process CPU time, RSS, actual bond sizes,
cutoff and versions. Never extrapolate the earlier6.6/62.6s shallow timings
as measured timings for this circuit. The existing3-QPU-second result is
3x3 and must NOT be used as a6x6 speedup denominator.

Expected before running: normalized local moments in physical bounds, initial
N=32, exact untruncated small systems conserve N. Low chi may converge poorly
as repeated mode permutations spread entanglement across the MPS cuts.
Timing is unknown; each reported time must come from a completed worker.
