# Conditional next step: matched central twirl1 hardware robustness

Status: PREPARED ONLY, NOT EXECUTED. Requires all three independently audited
twirl1 operator gates to pass. No QPU submission, remote retrieval, publication,
6x6 extension, automatic retry or new tensor-network batch.

This is a reused-data robustness check, not a blinded holdout. Twirl1 appeared
in the older low-chi eight-twirl aggregate. Do not select another twirl, subset,
seed, regularizer or observable based on measured performance.

## Freeze matching coefficients before scoring

Use only the saved twirl1 central Z_up and Z_down Grams at chi128 and onsite
ZZ at chi256, after their declared low/high-chi checks and independent audits.
Verify archive/job/layout/masks/calibration and state/Gram/source hashes.
Do not use twirl0 coefficients or an eight-twirl channel mixture.

Preserve the raw Grams and use the separately justified exact ideal F00=1
copies for fits. Fix eta1 and N=(43,7,14). Use all four possible central outcomes
to compute each readout-corrected score range and its variance penalty v/N.
Freeze all three point coefficient vectors, Gram sources and exact subsets
before accessing target means or the exact reference for accuracy scoring.

## Matching target data and budget

Archived job daem7r642tqs73autong on ibm_phoenix:
twirl1 native provider indices25/19/2 at CZ factors1/2/3.
Read exactly these target records and the shared all0/all1 calibration records.
Verify keys, masks, physical-to-classical mapping and64/7/14 target counts,
plus64 shots per calibration state. No live device connection.

Keep the previous deterministic factor1 split: one permutation of64 indices
with seed2026090917, first43 shared, remaining21 baseline-only.
Never change the seed or order after inspecting target outcomes.

Primary methods:
- Readout-only:64 factor1 target shots.
- Linear ZNE:43/7/14 target shots, weights(4/3,1/3,-2/3).
- Shot-aware L-MPF:43/7/14 target shots and each operator's own frozen Gram.

Each primary estimator uses64 target shots plus the same128 calibration shots:
192 archived shots per estimator, not new resource consumption. Their shared
data union is85 target plus128 calibration shots. A raw64 estimate may be
shown as a diagnostic without claiming it used calibration. No all85 L-MPF
accuracy comparison against a64-target-shot baseline in the primary table.

## Uncertainty and independent audit

Use10,000 stratified paired bootstrap replicates, fixed seed2026090918.
First draw the shared Jeffreys calibration posterior, then the four target
multinomial strata(43,21,7,14), preserving both-bit correlations. This RNG order
matches the earlier protocol. Save every draw; no seed scans or silent redraws.

Readout inversion occurs BEFORE unmasking. In each replicate recompute the
shot-aware penalty and coefficients using only that calibration draw and the
fixed matching Grams, then apply them to the paired target samples.
Also retain fixed-calibration and frozen-point-weight uncertainty diagnostics.

Compare central charge, spin=n_up-n_down and doublon estimates to the exact
finite-CIRCUIT reference using the same conventions:
charge=1-(Zu+Zd)/2, spin=(Zd-Zu)/2, D=(1-Zu-Zd+ZZ)/4.
This is not an exact exp(-iHT) reference without a separate Trotter error check.

Report signed/absolute errors, paired baseline-minus-LMPF absolute-error
improvement intervals, raw Pauli values and all four reconstructed joint
probabilities. Retain negative probabilities, out-of-range Pauli estimates
and failed comparisons. No clipping, number projection or reference-assisted fit.
Single-centre values cannot establish total N or full3x3 profile accuracy.

The95% percentile intervals are heuristic, especially for7 folded shots and
unseen outcomes. They exclude device-model/TN/drift/correlated-readout bias.
Do not present inclusion/exclusion of zero as guaranteed statistical coverage.

Independently replay subsets and bootstrap draws, reconstruct readout scores
with assignment-matrix inversion, solve KKT systems and recompute all physical
transforms, budgets and intervals. Check all methods use the same target
reference only AFTER fitting, never to train or choose coefficients.

Keep any comparison to the earlier twirl0 sample clearly secondary; do not
artificially pair independent cross-twirl shot draws merely by a shared RNG seed.
Report new classical mitigation/precomputation time separately. No new timing
advantage follows from these operator checks or archived-shot reanalysis.
