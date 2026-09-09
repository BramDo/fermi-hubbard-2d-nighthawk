# Frozen central-operator weights against matching archived hardware

Exploratory follow-up on the same existing data, not an independent hardware
experiment. No new QPU job, 6x6, publication, target-assisted coefficient fitting,
or full 27-observable/eight-twirl claim. Preserve earlier results and failures.

Use only job daem7r642tqs73autong, ibm_phoenix, 3x3, twirl0. Central Pauli
operators are indices8,9,22. Freeze the latest ridge1/56 weights from the
verified exact-norm follow-up: chi128 for Z_up/Z_down, chi256 for ZZ. Do not
refit, rescale, select variants by target accuracy, or use one-twirl weights
on the eight-twirl average. Verify archive/receipt/plan/QPY and coefficient hashes.

Available data: 64 factor1, 7 factor2 and14 factor3 target shots, plus64 all-zero
and64 all-one shared calibration shots. No shots are discarded from the archive.
Primary matched comparison: readout-only uses64 factor1 shots; linear ZNE and
L-MPF use43 factor1 +7 factor2 +14 factor3 =64 target shots. Each uses the same
128 calibration shots:192 allocated archived shots per primary estimator.
Raw64 (no calibration) is diagnostic. L-MPF with all64+7+14 target shots is a
separately labelled secondary result costing213 including calibration, not a
matched-budget improvement. The union of selected source data is213 shots.

Choose the shared43 factor1 shots by one fixed permutation, seed2026090917,
before inspecting accuracy; the remaining21 are baseline-only. Save both index
lists. Do not search seeds or choose a favourable subset. This avoids relying
on acquisition order and differs explicitly from the old first43 convention.

Independent assignment readout model: Jeffreys posterior means for P(1|0) and
P(0|1), from the two calibration circuits. Invert readout BEFORE undoing the X
mask. Onsite ZZ is the mean of products of corrected per-shot Z estimators,
not the product of their means. Identity terms stay exact and separate.
Report central-site charge=1-(Zu+Zd)/2, spin=(Zd-Zu)/2,
doublon=(1-Zu-Zd+ZZ)/4. This charge is not total lattice N.

Primary uncertainty:10,000 paired categorical bootstrap replicates, seed2026090918.
Four strata are shared43, extra21, factor2_7 and factor3_14. Resample each as a
multinomial over all four measured central-bit outcomes. This is equivalent to
row-resampling the observed data and preserves Z/ZZ correlations. Use a shared
Jeffreys calibration draw per replicate across all arms/methods. Also compute
fixed-calibration bootstrap uncertainty separately. If inversion is ill-conditioned,
record failure; do not silently reject/redraw. Save counts, errors and all arrays.

Report central values, absolute errors against the exact finite-circuit
reference and paired baseline-minus-LMPF absolute-error intervals for readout
and linear ZNE. A positive difference means improvement. Intervals are heuristic
95% percentile intervals, NOT coverage-certified confidence or p-values. Seven
shots are especially restrictive; empirical resampling cannot account for unseen
rare outcomes. Exclude claims of full noise-model, TN, drift or correlated-readout
uncertainty coverage. Do not clip Pauli values or reconstructed probabilities.

Independently audit point estimates and every bootstrap replicate using the
explicit two-bit assignment matrix inverse, not the production moment formula.
Reconstruct seeds/subsets, budgets, physical transforms and paired intervals.
No automatic go for6x6, regardless of central numerical outcome. The next decision
must reflect both sampling limitations and the still-unvalidated noise surrogate.
