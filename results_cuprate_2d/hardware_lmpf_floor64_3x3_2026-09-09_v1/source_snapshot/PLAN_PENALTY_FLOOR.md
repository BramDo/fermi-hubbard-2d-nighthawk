# Frozen exploratory protocol: penalty floors at higher actual shots

Use exactly the four combinations actual_n in[256,512], penalty_cap in[64,128].
Effective denominator d=min(actual_n,penalty_cap).
P_oa=range(score_o,a)^2/(4d), eta1, sum_a c_oa=1.
This is a NEW exploratory regularization rule. No measured target frequencies,
exact noiseless reference or reference-error score may enter the selection.

Reuse the verified budget-v2 Grams, noisy q distributions and8192 future
calibration draws, seed2026090921. No new QPU or high-bond state propagation.
Do not edit prior numerical sources or output. Total local compute<=120s.

## Equations and reuse identity (dimensionless except archived time)

For each calibration e_hat, use the same inverse-readout scores and the
existing penalty solver at d. Since exactly these d=64/128 computations are
already saved with the identical inputs and draws, their weights and means
can be reused byte-for-byte. Independently recompute them with the KKT oracle.

At FIXED d, changing actual shots leaves weights and conditional means
unchanged. All four independent strata scale together:
[n,2n,n,n]. Hence conditional sampling covariance at n equals
(d/n) times the saved conditional sampling covariance at d.
Calibration-mean covariance is unchanged; total=S_d*d/n+C_d.
This is not1/sqrt(n) scaling of the TOTAL SD because calibration stays finite.

For comparison with original1/n L-MPF on the SAME future shot samples,
build a joint15x15 covariance for
[raw,readout,ZNE,original L-MPF,floored L-MPF] x[charge,spin,D].
Use the actual n in every categorical covariance. Include shared calibration
and weight dependence through the same finite mixture, not derivatives.

For an outcome-score matrix B_s at each stratum s, conditional covariance is
sum_s [B_s^T diag(q_s) B_s - mu_s mu_s^T]/N_s.
Average over calibration and add covariance of the conditional means.
Paired differences use full cross-covariance, not independent-error sums.

From a physical vector(Q,S,D), probabilities in order[00,10,01,11] are
[1-Q+D,(Q+S)/2-D,(Q-S)/2-D,D].
Keep negative values. Check the mean forecast and every conditional forecast.
These are conditional model means, not sampled hardware estimates;
their positivity does not guarantee positivity of an actual finite-shot result.

## Locked comparisons, expectations and tests

Compare all candidates to original1/n, linear ZNE and readout at SAME actual
shot budget; primary3n target shots, union5n+512 including calibration.
Retain original time scenarios from the verified budget, with no fresh
billing guarantee. No larger shot count, new floor, new seed or changed eta.

Expect lower sampling variance than the original adaptive512 rule, but do
not assert improved physical accuracy. A stronger penalty can leave more bias.
Keep all model means, negative probabilities, stability failures and tradeoffs.

Tests:
- d=n exactly recovers the original mixture.
- Conditional covariance scales d/n with fixed d, calibration covariance
  and conditional means do not scale.
- Equal weights on the same samples give zero paired-difference variance.
- Independent small-mixture assignment/KKT/categorical covariance agrees.
- All probabilities sum to1; invalid examples remain negative, not clipped.
- Reject invalid denominators and inconsistent array shapes.

Independent full audit replays original calibration counts, recomputes KKT
weights on1,406 unique calibration outcomes at each d, and constructs actual-n
categorical covariance through a separate16-dimensional block covariance.
Verify every candidate's joint matrix, means, weights, paired SD and local
flags. No failed derivative-based covariance from budget-v1 is used.

Do not call a candidate hardware-ready. Descriptive candidates can pass
the previous .05 coefficient-change threshold in at least99% of these
planning draws and have a valid average local model probability vector.
These are exploratory screening criteria, not physical validation.
Report them without claiming a unique best accuracy. A fresh hardware test
still needs explicit backend, exact shots and cap approval plus live preflight.
