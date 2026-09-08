# Conditional 3x3 to 6x6 extension

Request: execute 3x3, then 6x6 only if 3x3 is OK. Existing hardware only;
no new QPU job, publication or push is authorized.

## Frozen first-stage choices

Use all 24 saved native target circuits (three CZ-folding arms, eight twirls)
from job daem7r642tqs73autong. Keep physical measurement-wire mapping and undo
readout masks after inverting readout. All physical preparation gates are
included in the channel; the input before those gates is the vacuum bitstring.
Use the saved per-gate depolarizing Lindblad surrogate, explicitly not learned.

Batch the chi=1 operator TN exactly as product factors, avoiding dense 4^18
arrays and unnecessary BP contractions of bond-one edges. This is only the
chi=1 limit of the previous method, not a nontrivial large-chi loop demonstration.
Compare this implementation with quimb chi=1 and independent dense small cases.

Each arm is the equal mixture of its eight circuit-adjoint observables. Gram
matrices must contain ALL cross-twirl terms, not merely averaged within-twirl
Grams. Freeze coefficients before evaluating target-state reference accuracy.

Equation registry (dimensionless normalized Hilbert-Schmidt coordinates):

| Formula | Implementation |
| --- | --- |
| O ~= amplitude * tensor_product(local) | product.evolve_products |
| F_ij = mean_ab inner(O_ia, O_jb) | product.gram_mixtures |
| min c.T G c - 2 b.T c, sum(c)=1 | fit.fit_coefficients |
| Optional ridge ||c||^2/min(shots) | fixed ridge=1/56, not target-tuned |
| z_corrected = (z - (e1-e0))/(1-e0-e1) | hardware_inputs.moment_samples |
| charge=1-(Zu+Zd)/2, spin=(Zd-Zu)/2, D=(1-Zu-Zd+ZZ)/4 | model.physical_transform |

Primary L-MPF uses fixed ridge 1/56 because the smallest existing arm has only
56 shots; unregularized results remain visible. Rate scale sensitivity at
0.7, 1.0, 1.3 is a diagnostic, not a confidence interval.

Equal measurement budget: readout baseline uses 512 base shots plus 128
calibration. L-MPF and ZNE use 344/56/112 target shots plus 128 calibration,
also 640. The first 43 of 64 shots in each base twirl are shared; the remaining
21 are baseline-only. All 808 archived shots are preserved, none overwritten.

## Stage gates (set before examining 3x3 L-MPF output)

1. Native circuit identity/hash/bit order checks and ideal finite-circuit
   reference checks pass. The reference is not exact continuous dynamics.
2. No NaNs, invalid Grams, or coefficient sum errors. Report small singular
   gaps, coefficient norms, truncation bounds and all bad outcomes.
3. Against both matched-budget readout and linear ZNE: central family RMSE
   may not worsen by more than 0.02 absolute for any of charge/spin/doublons.
   At least one family's improvement must have a positive paired 95% interval.
4. Propagate shot covariance and shared calibration posterior; bootstrap
   the shared base subset and baseline-only subset separately. Intervals are
   heuristic and exclude hardware drift, correlated noise and model bias.
5. At least chi=1 to chi=2 stability and an independent device-noise/forward
   validation are needed before 6x6. Do not treat a small ideal TN error or
   an improved N alone as passing. No higher-cost stage after an earlier gate
   failure. Conditional 6x6 authorization does not waive these checks.

First-stage local time cap: 1200 seconds, <=18 qubits; no density matrix.
Preserve intermediate factor/twirl states and hashes to avoid repeating work.
