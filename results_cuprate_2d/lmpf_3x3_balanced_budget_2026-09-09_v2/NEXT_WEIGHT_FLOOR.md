# Prepared only: stable penalty floor at higher actual shots

Status: NOT EXECUTED. No QPU or extra operator propagation authorized.

The budget check reveals that the current penalty shrinks as1/n, allowing
larger weights and failing the ZZ local stability check at512 shots.
A bounded offline follow-up can separate actual sampling from penalty strength.

Predefine effective penalty denominators64 and128, with actual shot counts
256 and512. Use P=range(score)^2/(4*min(actual_n,denominator)).
This is a NEW exploratory regularization rule, not a retest of the old
unchanged algorithm. Do not tune the denominator on observed target values
or exact reference errors.

Reuse the frozen Grams, noisy model probabilities and the same8192 calibration
draws. Recompute coefficients using the effective denominator; compute actual
sampling covariance using the actual n. Compare every candidate with the
original eta1/n rule and linear ZNE under the same actual shot/time budget.
Keep actual total exposure5n+512 and baseline3n unchanged.

Report coefficient-stability changes and simulated pass fractions, full and
paired covariance, conditional model means and invalid local probabilities.
No clipping, no mandatory positivity projection, no reference-assisted fit.
A smaller variance or more stable coefficient does not by itself demonstrate
better physical accuracy. Preserve all rejected candidates.

Maximum120s local computation, no live job submission and no6x6 escalation.
A later hardware test still needs explicit backend, shot and cap approval
and a fresh live compatibility/calibration/budget preflight.
