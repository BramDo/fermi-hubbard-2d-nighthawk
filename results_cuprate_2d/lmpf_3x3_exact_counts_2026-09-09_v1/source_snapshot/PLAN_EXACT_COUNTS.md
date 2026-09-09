# Frozen protocol: exact finite-count compatibility of twirl1 arms

Written before running the new statistical code. This is nevertheless
POST-HOC analysis of previously viewed data, not a preregistered experiment.

## Scope

Use the verified frozen-noise predictions from
results_cuprate_2d/lmpf_3x3_twirl1_noise_model_2026-09-09_v2,
and the original twirl1 central two-mode bitstrings from job
daem7r642tqs73autong on ibm_phoenix. CZ factors1/2/3, shots64/7/14.
No new QPU, no remote retrieval, no new TN states, no rate fitting.
The exact ideal reference is not used by these tests.

## Equation registry (all quantities dimensionless)

1. Joint probabilities in physical order [00,10,01,11]:
   p = (1+Zu+Zd+ZZ, 1-Zu+Zd-ZZ, 1+Zu-Zd-ZZ, 1-Zu-Zd+ZZ)/4.
   Code: joint_probabilities. Reject invalid probabilities; never clip.

2. Forward readout map: q_y = sum_x p_x A[y | x XOR mask],
   with independent single-bit assignment errors e0=P(1|0), e1=P(0|1).
   Code: measured_probabilities. Apply the mask BEFORE the assignment channel.
   Use the frozen shared calibration posterior mean (errors+.5)/65,
   NOT refitted target data. Treat it as a fixed parameter for the primary test.

3. Multinomial mass: P(C=c) = n! product(q_i^c_i/c_i!), sum(c)=n.
   Code: multinomial_logmass. Enumerate EVERY count vector with four outcomes:
   C(n+3,3)=47905,120,680 respectively. No empirical-support restriction.

4. Likelihood-ratio deviance:
   G(c;q)=2 sum_{i:c_i>0} c_i log(c_i/(n*q_i)).
   Code: deviance. If q_i=0 and c_i>0, G=infinity and model mass=0.
   Exact finite-sample tail: sum_{G(c)>=G(observed)} P(C=c).
   Inclusive ties; roundoff tolerance 1e-10*max(1,abs(G_observed)).
   Also evaluate tolerance1e-12 to check boundary stability.
   No asymptotic chi-square distribution, Monte Carlo sampling or mid-p.

5. Primary family: one joint-count deviance test per arm (three tests).
   Bonferroni adjusted p=min(1,3*p); descriptive alpha=.05.
   This controls a fixed three-test family conditional on an exact specified
   model and calibration, not the larger historical model-selection process.
   It is not an unconditional or held-out model-validation guarantee.

6. Secondary diagnostics: binary +1 counts for raw measured Zu, Zd and ZZ
   per arm. Sum the matching model q entries and use the same deviance-tail
   rule on all n+1 binary counts. Report all nine, with their own nine-test
   Bonferroni correction. Do not combine the primary and secondary families
   to claim one global significance level. These diagnostics are correlated.

## Pre-computation expectations and tests

Finite seven-shot tails are discrete, so the earlier bootstrap flag may not
survive a full count-level test. Do not predict a numerical p-value as a result.
All probabilities/tails must lie in [0,1] within floating-point tolerance.
Expectation identities: sum P=1, E[C]=nq, Cov(C)=n(diag(q)-q q^T).

Analytic tests:
- n=1, uniform four outcomes: every result tied, tail=1.
- n=2, uniform four outcomes, two identical outcomes: tail=1/4.
- Fair binary n=7 with six + outcomes: two-sided deviance tail=1/8.
- Deterministic channel: its only possible count has tail=1; impossible
  observations have tail=0.
- Zero readout is the masked permutation; asymmetric readout on physical00,
  mask10, e0=(.1,.2), e1=(.3,.4) gives (.24,.56,.06,.14).
- Permuting labels must preserve mass and tail.
- Invalid probabilities, noninteger counts and invalid masks must fail.

Production: stars-and-bars count enumeration, log-gamma mass, vector deviance.
Independent audit: nested-loop enumeration, integer binomial coefficients
times powers, scalar math.log deviance; additionally verify masses and binary
tails with SciPy. Preserve ties, rare counts, masks and all failures.
Save plan/source/input hashes before scoring, full enumerated distributions,
observed counts, statistics, p-values, timings and executed verification.

## Boundaries

Exact refers to exhaustive finite-count enumeration, computed in floating
point CONDITIONAL on fixed approximate TN/noise probabilities and readout.
No calibration uncertainty, model/TN uncertainty or shot drift is integrated.
Independent identically distributed shots are assumed, not validated here.
Failing to reject cannot prove the model correct or the hardware accurate.
No 6x6 go or quantum advantage claim follows. Maximum120s local computation.
