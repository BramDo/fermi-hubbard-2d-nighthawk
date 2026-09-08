# Experimental L-MPF route for the 2D Hubbard project

Reference: Robertson et al., *Lindblad Multiproduct Formulas*,
[arXiv:2609.05024v1](https://arxiv.org/html/2609.05024v1), submitted 4 September
2026; preprint. The implementation follows its observable-overlap objective,
not a fit to the target-state answer. This is an independently tested Python
implementation, not a reproduction of the authors' Julia software or 65-qubit DTC.

## Model and target

- First executed rung: 2x2 Hubbard, eight spin-orbitals, one hole, U=8,
  t=1, t'=-0.25, T=0.4, two symmetric product-formula steps.
- Original full-fermionic circuit builder, including Jordan-Wigner signs.
- Initial state and circuit parameters are in each run's `plan.json`.
- Ideal target is the **finite circuit**, not the exact Hamiltonian exponential.
- Native circuit is routed onto the saved Nighthawk 2x4 subgraph on physical
  qubits 102,103,104,105,112,113,114,115 of `ibm_phoenix`.
- Reference checks compare original/routed ideal observables and independent
  forward density-matrix versus backward Heisenberg-channel evolution.

## Overlap algorithm

For every Z mode and onsite ZZ observable separately, evolve its Pauli-coordinate
vector backwards through the native noisy circuit. The Pauli basis uses the
normalized Hilbert-Schmidt product Tr(A^dagger B)/2^n. The noisy channels act
after the corresponding gates forwards, so their adjoints act before the
unitary adjoints backwards. Qiskit's little-endian local axes are explicitly
converted to the tensor-network gate convention.

For ideal arm 0 and noisy arms 1,2,3, calculate the complete Gram matrix F.
Write G=F[1:,1:] and b=F[1:,0]. The primary coefficients solve

```text
minimize  c.T G c - 2 b.T c
subject to sum(c) = 1.
```

The fitting function accepts only the overlaps, not the initial state, target
expectation, hardware means or exact answer. Clifford rescaling is not used in
this first pilot: d=1. A separately labelled ridge variant adds
`(1/shots_per_arm)*sum(c_i**2)`. This is our fixed sampling-variance safeguard,
not part of the unregularized paper benchmark. An exact-overlap oracle is
included solely to validate the small instance; it is not a scalable proposal.

Operator states are genuine two-dimensional tensor networks, with dense 2-norm
BP used for gauging and gate truncation. Their overlaps use 1-norm BP plus the
loop-series expansion of quimb, rather than a 1D MPO middle-out contraction.
Bond dimensions 1 and 2 are tested initially; their comparison is not a
convergence certificate or a zero-truncation extrapolation.

The same low-bond tensor networks are also contracted exactly as a small-size
diagnostic. This separates state-truncation error from loop-contraction error.
Purely classical low-bond expectations are reported alongside hybrid estimates.

## Noise assumptions and sampling

The archived average gate infidelity r is converted to a local depolarizing
surrogate with p=d*r/(d-1), decay rate -log(1-p), and noise scales 1,2,3. This
is a valid Pauli-Lindblad channel family, but **not a learned sparse Lindblad
model of the device**. T1/T2, drift, correlated/coherent noise, and imperfect
preparation are not modelled. The saved independent readout probabilities are
used and treated as known in the simulated benchmark.

Aer performs finite-shot sampling, including readout. Each L-MPF/ZNE arm gets
512 shots; the raw and readout-only comparison each use 1536 base-noise shots.
They share the first 512 base shots with L-MPF/ZNE; the union is 2560 simulated
bitshots. All runs use zero QPU seconds. Equal shots are not a demonstrated
equal hardware time/gate budget, and simulated noise scaling is not a hardware
PEA implementation.

Charge, spin polarization and doublons are reconstructed from the Z/ZZ estimates
with their identity components kept exact and separate. N is not replaced by
its known value. Values and reconstructed probabilities are not clipped.
Cross-observable sampling correlations enter the propagated covariance.

For the small matched model, report both the observed one-seed errors and the
model-predicted RMS error including shot variance. These are not empirical
hardware confidence intervals. Fixed-coefficient shot uncertainty, TN error and
noise-model mismatch are distinct quantities. Noise-model scale variations
0.7 and 1.3 are sensitivity checks, not a calibrated uncertainty interval.

## Numerical safeguards and preserved failures

The first smoke run produced a non-PSD BP message and a NaN. It is preserved.
Exact <=2-qubit channel blocks, explicit BP-expression refresh after array
changes, positive tensor-norm balancing with retained scale factors, and PSD
checks were added. They do not shorten or change the quantum circuit.

A subsequent check exposed a signed-network issue in quimb 1.13's
`normalize_message_pair`: dividing both sides by sqrt(abs(m_i @ m_j)) leaves a
negative pair overlap at -1, although excitation projectors require +1.
The local `SignedD1BP` adapter uses a phase-preserving bilinear normalization.
Negative and complex message pairs, signed gauge-equivalent product networks,
and exact small-loop contraction are regression-tested. Installed libraries
are unchanged. Stagnating messages are not accepted as converged merely because
their rolling change is small; the absolute message residual is checked.

Large negative Gram eigenvalues are rejected, not silently projected away.
Only tiny roundoff-level negativity is tolerated. Failed fits and failed runs
remain visible and may not be promoted to accepted mitigation results.

After the sign correction, some chi=2 overlap BP contractions still produce
NaNs (including the uncorrected BP value). The log records invalid divisions;
no further cause is asserted without a reproducer. These LCBP fits are rejected.
The separately named exact-contraction backend can still evaluate the same
low-chi TN states. A complete observable-family score requires all twelve fits;
it never fills missing LCBP coefficients with exact-contraction coefficients.
Exact contraction on eight qubits does not establish scalable LCBP performance.

## Existing 3x3 and 6x6 hardware

The native folding data are prepared separately by `lmpf_2d/hardware_inputs.py`:

| Job | Size | Target shots at factors 1,2,3 | Readout calibration |
| --- | --- | --- | --- |
| daem7r642tqs73autong | 3x3 / 18 qubits | 512, 56, 112 | 128 |
| daen2vdnj4cs73afcn00 | 6x6 / 72 qubits | 4096, 4096, 4096 | 1024 |

The adapter validates job/plan identity, readout masks and bit order, preserves
all shots, and records conditional shot covariance plus a shared calibration
posterior covariance. It does not reuse 8-qubit coefficients on larger circuits.
CZ folding scales CZ exposure only, so its actual native channels must be used;
it is not equivalent to multiplying every noise rate in the pilot.

No learned Lindblad-rate files were found in these two job archives. Validated,
arm-specific overlaps and a learned or independently validated noise model are
still needed before claiming L-MPF mitigation of the 6x6 measurements. This
preparation is not a new mitigated hardware result and does not change the
historical TFLO/ZNE reports or the project's timing claims.

## Execution

Use the existing WSL interpreter `/home/bram/.venvs/qiskit/bin/python`:

```sh
python -B test_lmpf_2d.py
python -B test_lmpf_hardware_inputs.py
python -B lmpf_2d/pilot.py --output NEW_RESULT_DIRECTORY --chi 1 2 --budget-seconds 1200
python -B lmpf_2d/verify_pilot.py NEW_RESULT_DIRECTORY
python -B lmpf_2d/report.py NEW_RESULT_DIRECTORY
python -B lmpf_2d/hardware_inputs.py --output NEW_HARDWARE_INPUT_DIRECTORY
```

Every output directory is exclusive. Source snapshots, hashes, native QPY,
raw sampled bitstrings, overlaps, coefficients and rejection reasons are kept.
No cloud service is instantiated, no quantum job is submitted, and no article
is published. Qiskit 2.5.2 and quimb 1.13.0 are the tested installed versions;
the environment has not been downgraded to Qiskit 2.1.

## Subsequent actual 3x3 hardware application

On 2026-09-08, `lmpf_2d/archive_3x3.py` applied independently calculated chi=1
coefficients to the actual saved 3x3 CZ-folding data, using all eight twirls per
arm and all cross-twirl terms in the Gram matrix. This extends beyond the first
offline simulation pilot and beyond merely preparing input moments.

The native circuit channel includes its physical preparation gates; the input
before them is all-zero. A batched rank-one-SVD product TN implements chi=1,
checked against quimb on small tests and one native 18-qubit observable.
Three noise-rate variants and unregularized/fixed-ridge coefficients remain
separate. The known reference is used for validation, never coefficient fitting.

At an equal 640-shot budget including readout calibration, primary L-MPF
improves spin but worsens charge and doublons versus readout and linear ZNE.
Its central minimum reconstructed pair probability is -0.060244, not clipped.
The preregistered empirical guardrail fails, so the user-authorized conditional
6x6 step was not started. Device-noise and higher-bond validation remain open.
This is an exploratory application, not validated general-purpose hardware
mitigation. See [the full result and audit](../results_cuprate_2d/lmpf_3x3_hardware_2026-09-08_v1/DELIVERY.md).
