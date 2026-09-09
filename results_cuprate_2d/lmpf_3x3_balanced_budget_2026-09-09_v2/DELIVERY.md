# Offline 3x3 shot budget: time is not the main constraint

A fresh central 3x3 transfer test appears feasible in a few registered QPU
seconds under the archived timing assumptions. However, increasing shots
weakens the current shot-aware regularization and enlarges extrapolation
weights. The512-shot candidate fails the existing ZZ coefficient-stability
criterion;256 is borderline. More shots alone do not establish better mitigation.

Status: independently verified OFFLINE forecast, not authorized or submitted.
No cloud connection, new QPU job, new TN propagation, target fit or publication.

## Balanced design and time scenarios

n is the number of shots used at EACH folded CZ factor by ZNE and L-MPF.
The readout-only baseline uses3n factor1 shots, of which n are shared.
Thus the data union has3n+n+n=5n target shots. Fresh readout calibration
adds256 all-zero and256 all-one shots for every candidate.

| n per folded factor | Factor1 total | Total union incl512 calibration | Shot execution, old1us rep | 1-subjob estimate | 2-subjob estimate | 2 subjobs,250us rep sensitivity |
|---|---:|---:|---:|---:|---:|---:|
| 64 | 192 | 832 | .010911s | 2.010911s | 4.010911s | 4.218079s |
| 128 | 384 | 1,152 | .020103s | 2.020103s | 4.020103s | 4.306951s |
| 256 | 768 | 1,792 | .038485s | 2.038485s | 4.038485s | 4.484693s |
| 512 | 1,536 | 3,072 | .075250s | 2.075250s | 4.075250s | 4.840178s |

Each primary method has3n target shots plus its required calibration;
raw results are a diagnostic using the baseline's same target data.
Equal target-shot budgets are not equal gate-time budgets.

A5s maximum would be a PROPOSED cap, not existing permission. Three internal
subjobs already give approximately6s plus execution, so no candidate is
guaranteed to complete within5s. The number of internal subjobs is unknown.

IBM's current workload guide supports an approximate2s overhead per internal
subjob plus shot execution/repetition time. Usage is QPU reservation time,
not merely gate execution or user wall time. A smaller repetition delay may
increase preparation errors. Source checked2026-09-09:
[IBM workload usage](https://quantum.cloud.ibm.com/docs/en/guides/estimate-job-run-time).

The250us repetition delay is only a generic sensitivity scenario, not a claim
about the current ibm_phoenix default. These are not a quote, guaranteed charge
or elapsed-time forecast. A live preflight must refresh compatibility,
calibration, quota and timing before any submission.

## Actual circuits used in this estimate

Archived job daem7r642tqs73autong on ibm_phoenix, central twirl1 on3x3,
18 modes, N8, U8, T.4, two symmetric circuit steps. Physical layout and
original provider circuits are unchanged.

| Circuit | Provider index | CZ gates | Depth including measurement | Snapshot critical path |
|---|---:|---:|---:|---:|
| Readout all0 | 0 | 0 | 1 | 1.940us |
| Readout all1 | 1 | 0 | 2 | 1.980us |
| Factor1 | 25 | 1,008 | 630 | 21.012us |
| Factor2 | 19 | 2,016 | 788 | 32.980us |
| Factor3 | 2 | 3,024 | 918 | 40.596us |

Reset=.4us and rep_delay=1us are taken from the archived dispatch preflight.
Gate durations were reconstructed from the saved backend properties and
checked against the old aligned timings, then independently by Qiskit's
duration estimator on an offline Target. No new processor state was queried.

The older26-PUB/eight-twirl808-shot job recorded:
local shot estimate .018469216s, provider execution .024533248s, registered
usage3s, running-to-finished about15.763s. The provider execution is1.32833
times the local estimate; this discrepancy remains visible. Do not scale3s
linearly by the new shot count or turn the ratio into a guaranteed forecast.
The future design also has a different PUB composition.

## Forecast uncertainty including finite calibration

Each row below gives projected standard deviations for central
charge / spin / doublon probability. They include model shot variance and
finite calibration-mixture variance, not model/TN/drift error.

| n | Readout-only SD | Linear ZNE SD | Shot-aware L-MPF SD |
|---|---|---|---|
| 64 | .04796 / .04855 / .02141 | .12809 / .12931 / .06017 | .19767 / .19966 / .10246 |
| 128 | .03418 / .03460 / .01520 | .09068 / .09154 / .04257 | .16402 / .16568 / .08779 |
| 256 | .02454 / .02483 / .01084 | .06428 / .06488 / .03013 | .13014 / .13148 / .07041 |
| 512 | .01787 / .01807 / .00778 | .04567 / .04609 / .02134 | .10531 / .10639 / .05594 |

These are sampling precision forecasts, NOT absolute errors against truth.
Smaller readout SD does not imply its biased observable is more accurate.
L-MPF coefficients are recomputed for each n with the same eta1 rule,
so its SD does not follow a fixed-coefficient1/sqrt(n) law.

We simulated8192 future independent single-bit readout calibrations, seed
2026090921, with binomial errors drawn from the archived readout posterior
means. Each future error estimate uses (K+.5)/257. For each realization,
weights are recomputed and conditional target-shot means/covariances are
calculated analytically from the frozen two-bit model distribution.
No target measurements were simulated or used for fitting.

Total forecast covariance = average conditional sampling covariance
+ covariance of the conditional means. The full12x12 matrix retains shared
factor1 data and calibration across raw/RO/ZNE/L-MPF and their observables.
The largest total-SD change between4096-draw halves is .0000408.
This is a Monte Carlo sensitivity check, not a certified coverage bound.
IID shots, independent readout errors and a valid transferred noise model
are assumptions; drift, coherent errors, correlated readout, TN truncation
and noise-model bias remain outside this forecast.

## Coefficient stability and negative model forecasts

| n | Z_up low/high L1 change | Z_down change | ZZ change | Center flag | Simulated calibrations passing all local flags |
|---|---:|---:|---:|---|---:|
| 64 | .011900 | .013801 | .031388 | pass | 100% |
| 128 | .015042 | .017224 | .039104 | pass | 100% |
| 256 | .025647 | .026760 | .049225 | pass, near .05 | 92.96875% |
| 512 | .045607 | .047593 | .085190 | FAIL | 0% |

These percentages describe the planning model, not guaranteed future success.
The original pre-run resource rule selects256 because its center flags pass
and both two-subjob timing scenarios are below5s. Finite calibration reveals
why that candidate needs caution: about7.03% of simulated calibrations fail.
128 is the more conservative candidate under this additional diagnostic.
This judgment does not retroactively change the stored selection rule.

Projected L-MPF means from the noisy model, NOT measured quantum results:

| n | Charge | Spin | D |
|---|---:|---:|---:|
| 64 | .399922 | -.272533 | .013936 |
| 128 | .349527 | -.311041 | -.000496 |
| 256 | .320360 | -.335788 | -.007887 |
| 512 | .309338 | -.350501 | -.010036 |

Negative D is retained, not clipped. The512 case also has a negative inferred
up occupation since charge+spin<0. This warns that the current estimator
does not preserve all physical local probabilities even in its own model.
It would be inappropriate to promise a reliable answer simply by increasing shots.

## Recommendation and next action

Time-budget candidate:128 per folded factor,384 factor1 shots in the full
baseline,512 calibration shots,1,152 total shots, proposed maximum5s on
ibm_phoenix, subject to a fresh live preflight and explicit permission.
This would be an exploratory transfer/holdout test, not validated mitigation.

For the goal of better quantum results, first assess an explicitly frozen
regularization floor at higher actual shot counts; this may avoid relaxing
the penalty merely because more shots are available. See NEXT_WEIGHT_FLOOR.md.
That follow-up is prepared only. Neither it nor any new QPU job was executed.
No automatic6x6 escalation follows.

## Verification and preserved first attempt

The v1 derivative-based calibration forecast failed its independent audit:
the ZZ score-range penalty has tied extrema and a kink at symmetric
calibration. The output and failure are preserved. v2 replaces this with
discrete calibration mixtures; the failed derivative was not accepted by
loosening tolerances.

Nine tests pass. Independent replay checks8192 draws (1,406 unique outcomes),
four12x12 covariances, high/low KKT weights, shared-data contrasts and five
original circuits. Maximum weight difference1.69e-14; covariance3.54e-16.
v2 main calculation2.179209s; audit9.002651s, excluding Python startup.
No new QPU or TN states. Prior operator preparation is not included.

See VERIFICATION.md, source snapshots, complete JSON and covariance archive.
Nothing was pushed or published.
