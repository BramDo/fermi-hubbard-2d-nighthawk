# Readout + TFLO versus readout + ZNE: exploratory 512-shot pilot

Frozen before new calibration/training sampling, 2026-09-06. Offline only.
Reuse the archived U8,T=0.4 measured Aer bitstrings; therefore this is a
retrospective extension, NOT an independent confirmation of earlier ZNE.
Same 3x3 spinful Hubbard, 18 modes, two Trotter steps, physical layout,
native circuits, eight masks/twirls, saved ibm_phoenix calibration and full
Aer model. Target is the exact finite Trotter circuit, not exact continuum
dynamics. No provider calls, new hardware shots, or 5-second budget change.

## Fixed budgets and controls

Each main arm costs 512 measured shots, including overhead:

| Arm | Calibration | U0 training | U8 target shots |
|---|---:|---:|---:|
| Raw | 0 | 0 | 512 factor1 |
| Readout only | 128 | 0 | 384 factor1 |
| Readout + TFLO | 128 | 6 x 32 = 192 | 192 factor1 |
| Readout + linear ZNE | 128 | 0 | 216,56,112 at factors1,2,3 |

Calibration: two all-zero/all-one 18-qubit circuits, 64 shots each,
under the same full noise model (including X preparation error).
Training: original U=0 times0,.1,.2,.3,.4,.5; four shots per original twirl.
TFLO target first24 shots/twirl; readout-only first48; ZNE first27,7,14.
ZNE weights remain [4/3,1/3,-2/3]; allocation is the discrete minimum of
sum(w^2/n) for48 shots/twirl, no optimization against observed outcomes.
Shared data save execution but each arm is charged its full logical budget.
Both training and target circuits retain1008 CZ each, verified before use.
TFLO:387072 CZ; ZNE:669312 CZ; readout-only:387072 CZ; raw:516096 CZ.
Equal shots do NOT imply equal gates, scheduled duration or billed QPU time.
New work:192 training +128 calibration=320 Aer shots. Existing data unchanged.

## Equation registry and conventions

All occupations, Z moments and RMSE dimensionless; spin=n_up-n_down (not S_z).
Times are hopping units, hbar=1. Z=1-2n; little-endian arrays q0..q17;
site i has modes2i,2i+1. Quantum bitstrings are printed MSB-first.

For each physical wire q, e0=P(y=1|prepared0), e1=P(y=0|prepared1).
Estimate each as (errors+1/2)/(64+1), a Jeffreys posterior mean; calibrations
include X preparation error, so this is an approximate SPAM calibration.
For known readout mask m, a=(-1)^m(e1-e0), b=1-e0-e1.
E[Z_corrected]=(E[Z_decoded]-a)/b.
E[Zq Zr_corrected]=(E[Zq Zr]-a_q E[Zr]-a_r E[Zq]+a_q a_r)/(b_q b_r).
These tensor-product inverse moment corrections assume independent readout.
This is NOT M3 or TREX implementation and does not correct correlated readout.
Refuse denominators<=0.2; never clip unphysical output probabilities/moments.

Fit existing per-Pauli y=m*x+c*T+b with fixed ridge0.001 towards identity,
using ONLY six U0 references and readout-corrected training moments. Correct
target with the SAME calibration before applying the newly fitted model.
No postselection in this pilot: conditioning and inversion do not commute.
This is not a repeat of the earlier hardware postselection+TFLO protocol.
An uncorrected-input TFLO refit and ZNE without readout are paired diagnostics,
not budget-optimized competing arms. Classical control is exact U0 FLO atT=.4.

## Uncertainty and validation

Fixed-twirl paired resampling of complete shot vectors preserves site,
Z/ZZ, shared-prefix and cross-method dependence. Factor1 strata24,3,21,16;
factor2 first7; factor3 first14; each of48 training blocks contains4 shots.
2000 replicates, seed2028500000. Each replicate draws one shared calibration
from independent Beta(errors+.5,64-errors+.5) posteriors and refits TFLO.
The reported95% ranges are HYBRID bootstrap/calibration-posterior uncertainty
intervals, NOT guaranteed frequentist confidence intervals. Jeffreys prior
avoids falsely exact zero-error calibration at this very small sample size.
Also report fixed-calibration bootstrap and known-readout-matrix diagnostic;
the known-matrix diagnostic is an oracle, NOT a free experimental calibration.
Compare200/1000/2000 replicate quantiles; never use them to select a method.
No extrapolation/transfer/model bias, hardware drift or X-preparation systematic
is covered by the statistical intervals. Four training shots/twirl are sparse;
bootstrap cannot establish full training-distribution convergence.

Primary endpoint: site spin-RMSE(readout+ZNE)-spin-RMSE(readout+TFLO),
positive favoring TFLO. Charge/doublon RMSE, full Pauli MSE, local physical
bounds and comparison to classical FLO are mandatory guardrails, not selectors.
No advantage, hardware improvement, general superiority or matched-time claim.

Before sampling: unit tests for inverse-matrix orientation, asymmetric masked
readout and ZZ covariance, noise-free limits, singular calibration rejection,
allocation, shared prefixes, and no U8 fitting. Every training QPY noise-off
checked against its archived reference, normalization and Nup=Ndown=4.
Archive all raw Aer memory, counts, calibration counts, model, seeds, QPY,
source/input hashes, corrected moments, fit and bootstrap draws. Refuse overwrite.
Training seed2028100000+10000*setting+1000*twirl; calibration2028200000+1000*state.
These do not overlap the archived20271/20272/20273 ranges. No seed retries.

References: https://arxiv.org/abs/2102.02120 (TFLO principle);
https://qiskit.github.io/qiskit-addon-mthree/ (measurement mitigation context).
This small local inverse-moment implementation is distinct from that package.
