# Correction before execution: finite calibration mixture

The v1 independent audit detected a non-smooth score-range penalty at the
symmetric calibration center. Do not relax its tolerance or claim a smooth
Jacobian. Preserve v1 and its failed audit. Replace ONLY calibration
propagation, leaving the balanced shots, fixed Grams, q probabilities,
native circuits, timing scenarios and point coefficient stability rule unchanged.

Use8192 future calibration draws, seed2026090921, shared across all methods
and all four n candidates. K[state,mode]~Binomial(256,e_saved[state,mode]).
Each estimate is (K+.5)/257. This includes the actual discrete Jeffreys
estimator, its finite-sample bias and the non-smooth recomputed weights.
No target shots are Monte Carlo sampled and no target data are fitted.

For each calibration realization:
- Recompute inverse-readout scores, eta1 penalties and high/low weights.
- Compute exact conditional mean and shared-target-shot covariance using
  the frozen four-outcome q distribution and strata[n,2n,n,n].
- Apply law of total covariance:
  E_cal[Cov_target(Y|cal)] + Cov_cal(E_target[Y|cal]).
  Estimate the first term by the draw average and the second by sample
  covariance (ddof1). This is a parametric planning simulation, not a
  confidence interval, posterior truth probability or exact hardware forecast.
- Keep weights' low/high stability flags at the deterministic expansion
  center from v1, and additionally report the fraction of calibration draws
  passing the previous .05 coefficient-change threshold. Do not silently
  convert an almost-passing case into hardware-validation approval.
- Save means, high/low weights and K for every draw, plus full12x12
  conditional-average/calibration/total covariances. Report first-versus-second
  half SD differences as a finite Monte Carlo sensitivity check.
- Retain negative projected doublon means; no clipping or target-informed
  change of eta, noise rates or shot candidates.

Independent audit: group identical four-coordinate K outcomes, evaluate
each unique outcome using the separate assignment-matrix/KKT oracle from
verify_balanced_budget.py, then weight by its count. Use Qiskit Target
duration checks for all five circuits. Reconstruct covariance and paired
differences independently. Do not use the failed complex-step Jacobian.

Tests: prior7 analytic tests remain, plus discrete-mixture covariance
agreement with the independent oracle and a constant-calibration limit.
No extra QPU or new operator propagation. Remain within the120s local budget.
The selected candidate remains a provisional resource-plan candidate, not
submission permission or a promise of improved L-MPF accuracy.
