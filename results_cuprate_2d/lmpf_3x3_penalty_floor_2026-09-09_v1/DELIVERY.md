# Penalty floor: stable512-shot coefficients with lower forecast spread

The cap64 rule passes the predeclared local screening checks at both256
and512 actual shots per folded factor. At512, forecast SD is33-35% lower
than the original1/n rule, while all8192 conditional calibration forecasts
have valid local probabilities. This is an OFFLINE result under the frozen
noise model, not demonstrated hardware accuracy or quantum advantage.

No QPU call, new TN propagation, exact-reference fitting, clipping,
publication or push was performed.

## What changed

The penalty denominator is d=min(actual_n,cap), with cap fixed at64 or128
BEFORE the new calculation. Actual sampling still uses256 or512 shots.
This prevents the correction penalty from weakening merely because more
shots become available. Eta remains1 and every observable's weights sum to1.

The old64/128 weights already correspond exactly to these inputs and the
same8192 calibrations, so production reused them without alteration.
The independent audit recomputed every distinct calibration's weights via
the constrained KKT solve. This is a new exploratory estimator rule,
not an unchanged rerun of the old algorithm.

No measured target frequencies or exact noiseless reference errors enter
the new forecasts or candidate screening. All four fixed candidates are kept.

## Four candidates

Forecast SD is for central charge / spin / D, including finite calibration
and shared shots. It is NOT absolute error against truth.

| Actual shots per factor | Penalty cap | Forecast SD | SD reduction vs original same-shot L-MPF | Coefficient pass | Valid conditional local forecast |
|---|---:|---|---|---:|---:|
| 256 | 64 | .098979 / .099974 / .051250 | 23.94% / 23.96% / 27.22% | 100% | 100% |
| 256 | 128 | .116073 / .117243 / .062089 | 10.81% / 10.83% / 11.82% | 100% | 42.16% |
| 512 | 64 | .070123 / .070826 / .036258 | 33.41% / 33.43% / 35.19% | 100% | 100% |
| 512 | 128 | .082204 / .083030 / .043921 | 21.94% / 21.95% / 21.49% | 100% | 42.16% |

Percentages concern the8192 simulated calibrations, not a guarantee for future
hardware. Both cap128 candidates fail the average-probability screen because
their model mean D is negative. That failure is retained.

## Same512-shot comparison

All methods below use1536 primary target shots. Folded methods use512/512/512;
the readout baseline uses1536 factor1 shots. Sharing512 factor1 shots means
the total data union has2560 target +512 calibration =3072 shots.

| Method | Model mean: charge / spin / D | Forecast SD: charge / spin / D |
|---|---|---|
| Raw diagnostic | .623042 / -.107149 / .091538 | .01650 / .01670 / .00736 |
| Readout only | .615601 / -.109190 / .089019 | .01787 / .01807 / .00778 |
| Linear ZNE | .527742 / -.166056 / .055176 | .04567 / .04609 / .02134 |
| Original L-MPF1/n | .309338 / -.350501 / -.010036 | .10531 / .10639 / .05594 |
| L-MPF cap64 | .399922 / -.272533 / .013936 | .07012 / .07083 / .03626 |
| L-MPF cap128 | .349527 / -.311041 / -.000496 | .08220 / .08303 / .04392 |

The cap64 joint probabilities [00,10,01,11] of its mean forecast are
[.6140142166,.0497581541,.3222912286,.0139364007].
The smallest probability across all conditional calibration means is
+.0054525462. Cap128 instead reaches -.0098152249.
No negative values were removed or renormalized.

These probabilities are reconstructed from conditional MODEL MEANS, not
from future random hardware counts. Even the cap64 estimator can produce
negative estimates on an individual finite-shot run; it is not a positivity
projection or universal physicality guarantee.

A stronger penalty can leave more bias. Smaller spread and improved
coefficient stability do not prove smaller observable errors; the spin
forecasts, for example, change as the penalty changes. No exact-reference
accuracy ranking was computed or used in this task.

## Shared-data uncertainty and scope

The joint15x15 covariance covers
[raw,readout,ZNE,original L-MPF,floored L-MPF] x[charge,spin,D].
It retains common factor1 shots, all two-bit correlations and shared
calibration. At512/cap64, SDs of paired differences are:

| Contrast | Charge | Spin | D |
|---|---:|---:|---:|
| Floor minus readout | .062914 | .063511 | .033294 |
| Floor minus ZNE | .029886 | .030135 | .018626 |
| Floor minus original L-MPF | .050609 | .050934 | .026603 |

These are differences between estimator outputs, not evidence of improved
absolute error. Fixed-d conditional covariance scales as d/actual_n;
calibration-mean covariance does not. Both identities were checked.

We reused seed2026090921,8192 independent future single-bit calibration draws
(256 per prepared state, Jeffreys estimates). Target sampling covariance is
calculated analytically conditional on each calibration, then averaged and
combined with covariance of the conditional means. No derivative approximation
from the failed budget-v1 attempt was used.

Model/TN errors, coherent noise, drift, correlated readout and non-IID shots
are not included. The largest full-output SD change between calibration
halves was .0000408. The old raw-ZZ Gram failure and prior hardware shortcomings
remain in their original records. A new backend calibration may also invalidate
transfer of the archived noise model.

## Candidate and hardware authority

For a next independent3x3 hardware transfer test,512 actual shots per factor
with cap64 is a reasonable candidate under these exploratory screens.
Cap64 at256 is the smaller alternative. Neither is validated hardware.

A separate draft specifies the512 candidate on ibm_phoenix:
- 512 shared factor1 +1024 baseline-only factor1 shots;
- 512 factor2 and512 factor3 shots;
- 256 all-zero and256 all-one calibration shots;
- total3072 shots, one job, proposed hard maximum5 QPU seconds;
- original explicit twirl1 native circuits, manual masks, no runtime twirling
  or DD, no automatic retry or backend substitution.

See HARDWARE_CANDIDATE.md and hardware_candidate.json.
Status is NOT AUTHORIZED / NOT SUBMITTED. A fresh live preflight is required.
The previous archived timing scenarios are unchanged: about2.08/4.08s with
one/two internal subjobs at old1us repetition delay; three subjobs exceed6s.
Those are estimates, not a guarantee of completing within5s.
No6x6 escalation follows automatically.

## Verification and reproducibility

15 tests pass; all four candidates independently audited using1406 unique
calibration outcomes and actual-n count covariance. Maximum weight disagreement
4.61e-15, mean9.99e-16, covariance2.95e-16.
Main calculation3.390149s; audit9.692084s, excluding Python startup.
No new hardware or high-bond states.

The physics-verification workflow retained the rejected cap128 results,
kept precision separate from accuracy and required independent covariance
reconstruction. See VERIFICATION.md for actual executed output.
All inputs, numerical sources, forecast draws and joint matrices are preserved.

Reproduce into a NEW output folder:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 timeout --signal=KILL 60s /home/bram/.venvs/qiskit/bin/python -B lmpf_2d/penalty_floor.py --output results_cuprate_2d/lmpf_3x3_penalty_floor_reproduction
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 timeout --signal=KILL 60s /home/bram/.venvs/qiskit/bin/python -B lmpf_2d/verify_penalty_floor.py results_cuprate_2d/lmpf_3x3_penalty_floor_reproduction
```
