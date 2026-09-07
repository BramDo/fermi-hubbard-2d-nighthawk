# One 6x6 readout + CZ-folding pilot, max15 QPU seconds

User authorization: "Ja toestemming voor 15 sec", 2026-09-06.
One new Sampler job on ibm_phoenix (Nighthawk), saved account qiskit-runtime-q9.
No automatic resubmission, backend switching, batch or session. A durable exclusive
attempt marker is written BEFORE the sole submission call, including on ambiguity.

## Frozen physics and sampling

Full spinful fermionic t-t'-U swap-network circuit: 6x6 sites,72 modes,
4 holes, stripe-Neel, open boundaries, hopping t=1, t'/t=-0.25, U/t=8,
T=0.4, two steps, dt=0.2. Same network and conventions as the classical
full6x6 MPS benchmark, not the older simplified t-only baseline.
No exact72-mode statevector and no converged6x6 reference are available.

26 scalar PUBs,512 shots EACH: all0/all1 readout calibrations and
8 explicit Pauli twirls at each CZ factor1,2,3.
4096 shots per factor +1024 calibration =13312 total.
Raw4096 and mitigated13312 are NOT equal-budget arms.
Use the existing72-qubit path only after fresh full ISA/fault checks.
CZ baseline15400; factors15400/30800/46200 via exact adjacent CZ-pair insertion.
Never recompile after folding. Seed series202609040+t and2026300000+t.
Freeze randomized target-PUB ordering seed2026090615, calibrations first.
Calibration-only ordering cannot diagnose full-run drift.

## Budget

SamplerOptions.max_execution_time=15; default rep_delay unchanged;
built-in twirling and DD off because circuits already contain explicit twirls.
SDK and independent aligned critical-path timings include measurements;
add initialization reset and rep_delay to each shot. Require the SIX-subjob
planning scenario (12s approximate overhead plus shot execution) below15.
This does not prove the actual number of subjobs or guarantee job completion.
Verify remaining account usage >=15s and accepted provider cap after dispatch.
If failure or cap cancellation, preserve usage and failure; DO NOT retry.

IBM defines this limit as QPU usage, not wall time:
https://quantum.cloud.ibm.com/docs/en/guides/max-execution-time
Approximate2s overhead per unknown internal subjob:
https://quantum.cloud.ibm.com/docs/en/guides/estimate-job-run-time

## Verification and fixed analysis

Before submission: safety unit tests, small-system exact unitary checks,
fermionic sign tests reused from the classical benchmark, full72 structural
fold/replay, injective embedding and measurement-order checks, all26 QPY
roundtrips, transitive local source hashes and frozen input hashes.
No claim that structural checks constitute an exact72-qubit simulation.
Afterward: provider circuit/shot equality, result metadata/order checks,
lossless72-bit strings, provider metrics, hashes, and independent data checks.

Readout: independent asymmetric per-qubit confusion channels.
Jeffreys means (errors+0.5)/(512+1); include the explicit terminal readout-X mask
in each affine offset. Refuse inverse gain denominator <=0.1. No clipping.
Output72 single-Z and36 onsite-ZZ, all36 charge/spin/doublon observables.
Spin convention n_up-n_down, i.e. twice conventional Sz.

Primary ZNE: fixed ordinary linear fit through noise factors1,2,3,
intercept weights4/3,1/3,-2/3. Raw, readout, readout+ZNE, diagnostic ZNE-only.
No PEC, PEA, TFLO or postselection. No post-hoc fit/observable selection.
2000 whole-shot-vector bootstrap replicates at fixed twirls, shared independent
Jeffreys calibration draws; seed2026090616. Pointwise hybrid95% intervals,
not certified simultaneous coverage. Excludes drift, correlated SPAM,
extrapolation model bias, Trotter error and classical truncation.

Expected noiseless N=32, spin total0, probability and Pauli bounds; record
all violations without clipping. Conservation alone cannot certify profiles.
Report discrepancies against EVERY saved6x6 chi, not errors against exact truth.
The chi16->32 spin RMS difference0.1116 and max0.1652 fail the frozen
classical stability screen. No matched-accuracy or advantage claim is allowed.
For timing, fastest observed chi32 is32.183s with1thread, not178.599s with3.
Preparation, wall-clock service delay and QPU usage remain separate.

