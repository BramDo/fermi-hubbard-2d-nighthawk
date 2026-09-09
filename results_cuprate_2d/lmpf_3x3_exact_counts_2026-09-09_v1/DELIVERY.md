# Exact finite-shot check: the earlier factor2 ZZ flag is not confirmed

All three joint-count tests are non-rejecting, even before multiplicity
correction, conditional on the frozen model and fixed readout calibration.
The factor2 ZZ marginal has an exact deviance-tail p-value of 0.131992.
This does NOT establish that the model is correct or that shot noise is the
only remaining problem. No new hardware or improved mitigated estimates
were produced.

## Data and scope

Job `daem7r642tqs73autong`, backend `ibm_phoenix` (Nighthawk).
Archived twirl1 central-site 3x3 Hubbard measurements: CZ factors1/2/3 with
64/7/14 shots; shared 64 all-zero +64 all-one calibration shots.
18 modes, N8, U8, T0.4, two symmetric finite-circuit steps.
This is neither a full 3x3 lattice validation nor a 6x6 experiment.

Four-outcome order is [00,10,01,11], up-bit first and least significant.
Raw observed counts are [7,14,10,33], [2,0,1,4], [2,3,6,3].
Both central mask bits are1. The fixed noise-model probabilities were
first remasked and then passed through the forward readout assignment matrix.
Counts themselves were NOT inverted or clipped for the statistical test.

No target values or exact ideal reference were used to fit any probabilities.
The single-bit readout errors remain the saved posterior means:
e0=e1=.5/65 for both central modes. Treating these as fixed parameters
is a deliberate conditional analysis, not integration of their uncertainty.

## Primary joint-count tests

| CZ factor | Shots | All count vectors | Deviance G | Exact tail p | Bonferroni p (3 arms) |
|---|---:|---:|---:|---:|---:|
| 1 | 64 | 47,905 | 1.298586 | .731132 | 1.000000 |
| 2 | 7 | 120 | 5.030948 | .235440 | .706320 |
| 3 | 14 | 680 | 2.494818 | .510462 | 1.000000 |

We enumerate all nonnegative count vectors c with sum c=n, using the
multinomial probability n! product(q_i^c_i/c_i!). The statistic is

G(c;q) = 2 sum over c_i>0 of c_i log(c_i/(n q_i)).

The reported p-value sums the probabilities of every count vector with
deviance at least as large as observed, including ties. It is NOT the
probability that the noise model is true, nor just the probability of
observing exactly these counts. No large-sample chi-square approximation,
empirical bootstrap, Monte Carlo sampling or mid-p adjustment was used.

At descriptive alpha=.05, there are no primary rejections.
Bonferroni is for the specified three-arm family under fixed probabilities;
it does not correct all prior exploratory analyses or model choices.

## Secondary marginal checks

These use raw measured-bit plus counts and the corresponding forward-model
plus probabilities. They are separate, correlated diagnostics, not independent
pieces of evidence to multiply together.

| Factor | p(Z_up) | p(Z_down) | p(ZZ) |
|---|---:|---:|---:|
| 1 | 1.000000 | .604588 | .315993 |
| 2 | .700252 | .718208 | .131992 |
| 3 | .278341 | .796089 | .287788 |

All nine Bonferroni-adjusted marginal p-values equal1 after rounding.
The primary and secondary families are reported separately; no combined
global significance level is claimed.

### The seven-shot ZZ calculation in elementary form

Factor2 has six equal-bit outcomes (ZZ=+1) out of seven.
The model probability of an equal-bit outcome AFTER readout is

p = .5364938635076963.

The inclusive two-sided deviance tail consists of k=0,1,6,7.
Consequently its probability is exactly the finite polynomial

(1-p)^7 + 7p(1-p)^6 + 7p^6(1-p) + p^7
= .13199189474505665,

up to floating-point arithmetic. A separate PowerShell evaluation gave
.131991894745057 (display precision), with zero difference from the saved
enumerated value in double precision.

This raw count statement is consistent with the earlier readout-corrected
ZZ estimate .736782 versus frozen noisy prediction .075286. The discrepancy
in point estimates remains; its earlier bootstrap interval excluded the
model, whereas this different, explicitly specified finite-count test does not.

One reason to distrust overconfident seven-shot bootstrap tails is visible
in the data: the 10 outcome was never observed. A resample of those seven
shots cannot generate it, although the frozen measured-space model assigns
it probability .245516. The exact count test includes all possible outcomes.
This is a methodological diagnosis, not a proof that this feature alone
caused the entire bootstrap discrepancy.

## What this changes, and what it does not

The data do not currently provide convincing evidence against the frozen
noise model in these central arms under the specified conditional tests.
It is reasonable to proceed to planning a better-powered, fresh 3x3 check
without fitting this model to the same target measurements.

However:
- Low sample size also means low ability to detect model errors.
- Shots are assumed IID; drift and time correlation were not verified.
- Calibration uncertainty, correlated readout, TN truncation and noise-model
  bias are excluded from the conditional test.
- The data and earlier results were already viewed; this is post-hoc work,
  not independent held-out validation or a preregistered experiment.
- Earlier L-MPF central spin/doublon errors and unresolved paired improvement
  intervals are unchanged. We have not improved quantum measurements here.
- The ideal-reference and raw ZZ Gram-truncation limitations remain in the
  parent records. No reference is substituted into this count test.
- No 6x6 go, matched-accuracy advantage or extra-QPU authorization follows.

## Execution and audit

10 targeted tests pass. Main diagnostic 2.409858s; independent audit 1.918410s,
excluding Python startup. All 48,705 primary count vectors, three joint tails
and nine binary tails were independently checked. No new TN propagation
or QPU use; this is not a quantum/classical speed comparison.

Production uses stars-and-bars enumeration and log-gamma mass evaluation.
The verifier uses reverse nested-loop enumeration, integer binomial
coefficients times powers, scalar log statistics, a Kronecker assignment
matrix, and additional SciPy mass checks. Largest tail disagreement:
7.33e-15. Tightening tie tolerance from1e-10 to1e-12 changes no result.
Floating-point sums differ from1 by about1e-14 at most; raw sums are saved,
not silently normalized or clipped.

All source/input hashes, observed records, full enumerations, timings and
actual verification output are saved alongside this report.
See VERIFICATION.md and NEXT_3X3_BUDGET.md.

Reproduce into a NEW result folder in the existing WSL Qiskit environment:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 timeout --signal=KILL 60s /home/bram/.venvs/qiskit/bin/python -B lmpf_2d/exact_counts.py --output results_cuprate_2d/lmpf_3x3_exact_counts_reproduction
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 timeout --signal=KILL 60s /home/bram/.venvs/qiskit/bin/python -B lmpf_2d/verify_exact_counts.py results_cuprate_2d/lmpf_3x3_exact_counts_reproduction
```
