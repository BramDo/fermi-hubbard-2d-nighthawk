# L-MPF integration: offline first

Reference: Robertson et al., Lindblad Multiproduct Formulas,
https://arxiv.org/html/2609.05024v1 (4 September 2026, preprint).

Scope: implement Heisenberg-observable overlap minimization for this repository's
fermionic 2D Hubbard circuits. Keep raw, ZNE and L-MPF separate, preserve identity
terms, and do not fit weights to the desired target-state expectation value.

1. Validate exact local channel adjoints and the constrained Gram-matrix solver.
2. Connect 2D operator tensor networks and loop-corrected BP using available
   Python libraries; report all departures from the paper's Julia implementation.
3. Run a small 2x2 Hubbard (8-qubit) pilot with the archived Nighthawk calibration
   as a model, plus exact noiseless/noisy checks, matched shot accounting, and
   truncation/conditioning/model-mismatch diagnostics.
4. Inspect whether the existing 3x3/6x6 folded hardware records contain the
   necessary circuits, per-arm results, readout calibration and learned noise.
   Apply only supported offline post-processing and label model assumptions.
5. Save coefficients, overlaps, errors, input hashes, timings and negative tests.

No QPU submission, no publication, no modification of historical evidence.
The installed Qiskit version is retained; no downgrade to 2.1 is implied.
Ergodic amplification is not imported from DTCs without a separate Hubbard
validation. A low-bond result must not be called a validated large-scale result.

## Executed status, 2026-09-08

All five offline steps are complete. The full pilot v3 ran in 841.059 seconds,
with 23 regression tests and an independent saved-data audit. Chi=1 LCBP has
all twelve observable fits. Chi=2 LCBP fails for one observable (two rejected
fits including ridge); exact contraction of the same low-chi TN is reported
separately, not substituted silently. Unregularized chi=2 also exhibits severe
shot amplification, so a smaller systematic error alone is not success.

The hardware adapter processed the actual 3x3 and 6x6 folding archives but
does not claim L-MPF hardware mitigation. Validated arm-specific overlaps and
an adequate device noise model are still missing. No cloud jobs were submitted.

Evidence: `results_cuprate_2d/lmpf_2d_pilot_2026-09-08_v3/DELIVERY.md` and
`results_cuprate_2d/lmpf_hardware_inputs_2026-09-08_v1/summary.json`.
