# One fixed shot-allocation-aware regularizer, offline

This exploratory follow-up is chosen after the failed fixed-ridge pilot on the
same data. It is not blinded validation. Preserve that failure and all prior
data. No new QPU, chi increase, twirl mixture, all85 variant, 6x6 or publication.

Use the same central Z_up/Z_down/ZZ Grams, exact F00=1, twirl0, archived job
daem7r642tqs73autong on ibm_phoenix. Keep the previous seeded43/21 factor1 split,
7/14 folded shots, shared128 calibration shots and all10,000 paired bootstrap
draws. Primary total remains192 archived shots (64 target plus128 calibration).

Replace the scalar ridge1/56 by one predetermined diagonal penalty. For each
operator and arm, form the readout-corrected per-shot estimator for ALL four
possible measured central-bit outcomes. Let its minimum/maximum be m and M.
Set v=(M-m)^2/4 and Lambda_aa=v_a/N_a, N=(43,7,14). Use strength eta=1 exactly.
Do not add the old scalar ridge, scan eta, use target sample variances, look at
reference errors to choose weights, or select favourable seeds/methods.
Only G/b, known counts, masks and readout CALIBRATION determine the weights.

The variance bound follows from (X-m)(M-X)>=0, which gives
Var(X)<=(E[X]-m)(M-E[X])<=(M-m)^2/4. For independent shots, divide by N.
For independent arms conditional on the calibration, c^T Lambda c bounds
conditional sampling variance. It does NOT bound calibration/model/TN bias.

Minimize F00-2*b^T*c+c^T*G*c+c^T*Lambda*c, subject to sum(c)=1. This is a
surrogate bias/variance tradeoff, not a certified bound on actual hardware MSE:
the normalized-HS projection loss is not the true state-specific bias squared.
Expect possibly less sampling amplification and more projection bias, not
guaranteed better target accuracy. Save both objective components separately.
Validate original Grams before adding a penalty; never conceal invalid inputs.

Freeze the point weights before scoring target means. Check their change at the
same low/high chi levels against the existing0.05 coefficient-L1 criterion.
Retain the previous full-Gram/G/b scope and limitations; no new TN computation.

Primary uncertainty propagates calibration dependence of the new weights:
for each SAVED calibration draw, recompute Lambda and c using only that draw and
the fixed G/b, then apply it to the paired SAVED target bootstrap counts.
Also retain (1) frozen-point-weight uncertainty with varying calibration and
(2) fixed-calibration uncertainty. This is not target/reference refitting.
No silent calibration-draw rejection, clipping, N projection or positivity fit.

Compare central physical values/absolute errors to the exact finite-circuit
reference and report paired error-improvement intervals versus readout, ZNE
and the old fixed-ridge L-MPF. Keep the same heuristic95% percentile convention
and the warnings about unseen outcomes at7 shots and unmodelled correlated
readout, drift, TN error and noise-surrogate bias. No automatic go for6x6.

Independent audit: explicit assignment matrix solves to reconstruct the estimator
ranges and moment estimates, direct KKT solves instead of the production
null-space solve, and replay every calibration/target bootstrap draw. Run the
prior45 tests and six new bounded-variance/solver/invariance/rejection tests.
Save provenance, before/after coefficients, penalties, objectives, bootstrap
weights and outcomes. Do not modify historical numerical sources.
