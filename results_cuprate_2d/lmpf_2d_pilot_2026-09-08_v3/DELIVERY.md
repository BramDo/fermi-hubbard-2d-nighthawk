# Offline L-MPF pilot: completed with explicit rejected fits

Date: 2026-09-08. **No new QPU job; no validated 6x6 L-MPF hardware result.**

The project now has an executed, source-snapshotted implementation of the
[L-MPF observable-overlap objective](https://arxiv.org/html/2609.05024v1).
This is an independent Python implementation and a small matched-surrogate
validation, not a reproduction of the authors' 65-qubit DTC demonstration.

## What was actually run

- 2x2 full-fermionic Hubbard: eight qubits, N=3, U=8, t=1, t'=-0.25,
  T=0.4, two symmetric product-formula steps. Reference: ideal finite circuit.
- Frozen ibm_phoenix/Nighthawk 2x4 physical subgraph; native circuit depth
  1415, including 675 CZ gates. Classical block fusion did not shorten it.
- Local depolarizing Lindblad surrogate derived from saved gate infidelities;
  readout included. This is not a learned or validated device noise model.
- Three noisy arms at scales 1,2,3, 512 shots each. Baselines use 1536
  base-noise shots. Their shared samples give 2560 total simulated bitshots.
- Eight Z and four onsite ZZ operators. Coefficients depend only on their
  Hilbert-Schmidt overlaps, never on the initial-state target expectations.
- Genuine 2D BP-gauged tensor networks at chi=1,2, four-edge loop corrections,
  and an independent exact contraction of those same truncated networks.
- Fixed ridge = 1/512 is a separately labelled variance safeguard.
  No Clifford rescaling, ergodic amplification, or chi extrapolation.

## Predicted total error at the stated shot budget

Each entry is sqrt(mean(bias^2 + sampling variance)) over the four lattice
sites, under the matched simulation model. Lower is better. Cross-observable
correlations are retained. These are not hardware confidence intervals.

| Method | Charge | Spin | Doublons |
| --- | ---: | ---: | ---: |
| Raw (1536 base-noise shots) | 0.093319 | 0.299018 | 0.117569 |
| Readout only (1536 base-noise shots) | 0.094492 | 0.293403 | 0.118245 |
| Readout + linear ZNE | 0.066419 | 0.178820 | 0.093775 |
| Readout + quadratic Richardson ZNE | 0.126416 | 0.140952 | 0.083967 |
| Readout + L-MPF, 2D LCBP, chi=1 | 0.070402 | 0.075754 | 0.044271 |
| Readout + L-MPF, 2D LCBP, chi=1, fixed ridge | 0.066850 | 0.077166 | 0.044249 |
| Readout + L-MPF, exact low-chi TN contraction, chi=1 | 0.070402 | 0.075754 | 0.044271 |
| Readout + L-MPF, exact low-chi TN contraction, chi=2 | 0.178470 | 0.184286 | 5.224663 |
| Readout + L-MPF, exact low-chi TN contraction, chi=2, fixed ridge | 0.065942 | 0.077976 | 0.044395 |
| Readout + exact-overlap L-MPF oracle (not scalable) | 0.387357 | 0.395743 | 0.284994 |
| Readout + exact-overlap oracle, fixed ridge (not scalable) | 0.089049 | 0.086094 | 0.049563 |
| L-MPF oracle, model rates 30% too low | 0.271330 | 0.277444 | 0.179915 |
| L-MPF oracle, model rates 30% too high | 0.559365 | 0.577843 | 0.470870 |

## Systematic model error, excluding finite-shot variance

This second table separates error cancellation from shot-noise amplification.
Purely classical TN estimates have no shot variance in this comparison.

| Method | Charge | Spin | Doublons |
| --- | ---: | ---: | ---: |
| Raw (1536 base-noise shots) | 0.092076 | 0.298599 | 0.117253 |
| Readout only (1536 base-noise shots) | 0.093228 | 0.292964 | 0.117918 |
| Readout + linear ZNE | 0.051282 | 0.173432 | 0.090573 |
| Readout + quadratic Richardson ZNE | 0.027818 | 0.061936 | 0.044449 |
| Readout + L-MPF, 2D LCBP, chi=1 | 0.033486 | 0.040344 | 0.008663 |
| Readout + L-MPF, 2D LCBP, chi=1, fixed ridge | 0.029361 | 0.045670 | 0.014590 |
| Readout + L-MPF, exact low-chi TN contraction, chi=1 | 0.033486 | 0.040344 | 0.008663 |
| Readout + L-MPF, exact low-chi TN contraction, chi=2 | 0.025267 | 0.039295 | 0.833318 |
| Readout + L-MPF, exact low-chi TN contraction, chi=2, fixed ridge | 0.026697 | 0.046729 | 0.014645 |
| Readout + exact-overlap L-MPF oracle (not scalable) | 0.001471 | 0.009609 | 0.001377 |
| Readout + exact-overlap oracle, fixed ridge (not scalable) | 0.048362 | 0.037390 | 0.007074 |
| L-MPF oracle, model rates 30% too low | 0.012712 | 0.014251 | 0.002283 |
| L-MPF oracle, model rates 30% too high | 0.031104 | 0.094576 | 0.046708 |
| Purely classical low-chi TN, chi=1 | 0.126437 | 0.163908 | 0.013907 |
| Purely classical low-chi TN, chi=2 | 0.126364 | 0.163855 | 0.013898 |

## Rejections and verification

- 23 regression tests passed; all 12 saved operators were checked.
- 94 accepted TN coefficient sets rechecked for normalization,
  constrained optimality, and residual consistency.
- 2 TN coefficient fits were rejected and retained in summary.json.
- BP propagation updates that missed strict convergence: 0.
- Maximum saved sample reconstruction error: 0.
- Forward density evolution, backward Heisenberg evolution, native routing,
  bit order, fermionic circuit choice, covariance and source hashes checked.
- Verification certifies these software/model consistency checks, not hardware
  accuracy, tensor-network convergence, or the Hamiltonian-exponential target.

| Rejected method | Observable index | Reason |
| --- | ---: | --- |
| lmpf_2d_lcbp_chi2 | 2 | Loop-contraction failure; see loop_diagnostics |
| lmpf_2d_lcbp_chi2_ridge | 2 | Loop-contraction failure; see loop_diagnostics |

LCBP failures are not replaced silently. A complete method score is included
only when all 12 coefficients exist. The separately named exact-contraction
variant still truncates the operator TN at low chi, but contracts its overlaps
exactly on this small graph. It is not evidence that the scalable loop
approximation works on the failed cases. Inspect each operator JSON for
actual loop-vs-exact errors, warnings and Gram spectra.

## Existing 3x3 and 6x6 hardware: prepared, not mitigated with L-MPF

The separate [hardware input summary](../lmpf_hardware_inputs_2026-09-08_v1/summary.json)
preserves the real folding shots, corrects asymmetric readout before undoing
X masks, and estimates conditional shot plus shared-calibration covariance.
The 3x3 job is daem7r642tqs73autong; the 6x6 job is daen2vdnj4cs73afcn00.
This latter job is not the later original/compact seven-second TFLO job.

Their own validated arm-specific overlaps and a learned or independently
validated noise model remain missing. CZ-only folding is not the pilot's
all-gate noise scaling. Eight-qubit coefficients cannot be transferred to
18 or 72 qubits. No historical result or timing claim was overwritten.

## Reproducibility and evidence

- Full-pilot wall time: 841.059 seconds, including dense validation,
  multiple TN backends, sampling and diagnostics. This is not the timing of
  a production-only mitigation pass or a comparison with the 150-second 6x6 run.
- [Plan and circuit/noise identity](plan.json).
- [All numerical results and single-seed observed errors](summary.json).
- [Independent verification](verification/verification.json).
- [Input/output hashes](input_output_sha256.json); raw arm memory and native QPY.
- source_snapshot contains the actually executed pilot implementation.
- Earlier smoke failures and stopped/rejected pilots remain in neighbouring
  dated folders; they are not accepted hardware or mitigation results.
- [Protocol, conventions and limitations](../../theory/LMPF_PROTOCOL.md).

The physics-verification workflow required preserving failed loop contractions
and keeping shot uncertainty, approximation error and hardware validity separate.
No quantum advantage is established by this pilot.
