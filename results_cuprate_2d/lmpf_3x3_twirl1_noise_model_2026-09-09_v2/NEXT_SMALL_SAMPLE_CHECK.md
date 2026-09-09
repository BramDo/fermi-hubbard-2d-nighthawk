# Prepared only: count-level compatibility at very small shot counts

Status: NOT EXECUTED. No hardware budget or new TN propagation is authorized.

Before treating the factor2 ZZ bootstrap flag as evidence of a bad noise
model, check the original finite counts against the frozen model in measured
bit space. The current seven-shot empirical bootstrap cannot generate a
previously unseen outcome, so its narrow/discrete tails need a separate check.

Use all saved factor1/2/3 joint counts, fixed model predictions and the same
known masks and calibration. Do not select a favorable arm or refit noise
rates to these targets. Preserve the parent output and identify the analysis
as post-hoc on reused data.

A bounded local follow-up can enumerate the four-outcome multinomial
distribution at n=7 and n=14 (120 and 680 count vectors). Define the test
statistic and tail rule before running that code; include all three arm
diagnostics if making a family-wise statement. At n=64 there are 47,905
count vectors, still small enough for a guarded local calculation.

Use a valid model joint probability distribution mapped through the fixed
readout assignment and mask before evaluating probabilities of measured
counts. Reject invalid model probabilities instead of clipping them.
A fixed calibration-posterior-mean check is conditional, not calibration-free.
If including calibration sensitivity, keep shared uncertainty explicit and
do not call a posterior-predictive quantity a certified frequentist p-value.

Validate enumeration normalization and simple limiting cases independently.
No new QPU, no refitting, no high-chi propagation, at most 120s offline.
Failure to reject with these tiny samples is not noise-model validation.
Only after this diagnostic should a balanced-shot 3x3 budget be proposed;
a hardware submission still requires a fresh explicit backend/budget approval.
No automatic 6x6 escalation.
