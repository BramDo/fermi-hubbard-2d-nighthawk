# Frozen full 6x6 chi=64 continuation

This is one CPU-only, one-BLAS-thread continuation of the existing full fermionic
6x6 calculation. It does not alter the original benchmark or hardware inputs.
No quantum call, dependency installation, automatic retry, or chi=128 is allowed.

The circuit is the same 72-mode open-boundary stripe-Neel state with 4 holes
(32 particles, initially 16 of each spin), t=1, t-prime=-0.25, U=8, mu=0,
two steps of dt=0.2, and total T=0.4. The unchanged numerical kernel uses
10,224 adjacent fused fSWAP/hopping/interaction updates in 288 layers.
The MPS cap is chi=64, relative SVD cutoff 1e-10, complex128, with the same
layer normalization as the original benchmark.

Before running, check the original source hashes and entire classical archive,
and agreement with the hardware configuration and its shared source hashes.
Run the original small-system tests (full 2x2 state, observables, zero-U FLO,
unitarity, fermionic sign, target size/update count) and continuation guard tests.

Limits: 600 s kernel wall time, 650 s child-process wall time, 2 GiB RSS.
A Linux wall-clock alarm and the original between-layer checks bound the kernel;
the supervising parent independently samples time and RSS every 0.1 s and kills
only its owned child if a limit is crossed. RSS is a polled operational guard,
not an OS-level proof that no sub-0.1-s transient can exceed 2 GiB. A timeout or
memory stop yields no final physical estimate and no retry. CUDA is disabled.

Expected before computation: charge lies in [0,2], spin in [-1,1], doublon in
[0,1]; total number should be near 32. Sitewise changes from chi=32 are unknown
and need not be monotonic. The accumulated log retained norm is only a
truncation diagnostic, not a fidelity estimate or certified observable bound.

Compare all 36 sites and each of charge, spin, and doublon to BOTH existing
chi=32 one-thread and three-thread results, with RMS and maximum differences.
Also compare the two chi=32 profiles to expose thread/SVD sensitivity. Preserve
all signed site differences. Reuse the earlier heuristic screen (each RMS <=
0.01, maximum spin difference <=0.03, and final number error <=0.01), label it
heuristic, and do not promote this single refinement to certified convergence.
Do not treat chi=64 as exact, nor infer that chi=128 is required or sufficient.

No Monte Carlo sampling error applies to the deterministic MPS calculation.
MPS truncation, roundoff/thread dependence, product-formula discretization,
and unconstrained higher-chi convergence remain separate error sources. The
hardware comparison targets the identical finite-step circuit, not exact
continuous-time Hubbard evolution. Timing occurs alongside hardware archival
and other local work: measured kernel/cold-worker times are not an isolated
performance benchmark and do not alone demonstrate quantum advantage.
