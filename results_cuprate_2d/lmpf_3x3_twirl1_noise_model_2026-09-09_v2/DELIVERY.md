# Frozen noise-model check against the archived twirl1 arms

The factor1 predictions are compatible with the broad archived measurement
intervals. Factor2 has a large ZZ discrepancy, but only seven shots; the
empirical bootstrap cannot give reliable general small-sample coverage.
The diagnostic does not validate the noise model, identify a unique error
source, or establish that extra shots alone fix the mitigation.

Status: independently verified offline diagnostic. No new QPU use, no new
operator propagation, no model fitting, and no 6x6 go.

## Scope and conventions

Job `daem7r642tqs73autong`, backend `ibm_phoenix` (Nighthawk), archived
2026-09-06; only twirl1 and the central site of the 3x3 spinful Hubbard model.
Eighteen modes, N=8 (4 up + 4 down), t=1, t'=-0.25, U=8, T=0.4,
two symmetric product-formula steps. Observables [8,9,22] mean
Z_up on mode8, Z_down on mode9 and their onsite ZZ product.

Charge = 1-(Z_up+Z_down)/2; spin = (Z_down-Z_up)/2 = n_up-n_down;
doublon probability D = (1-Z_up-Z_down+ZZ)/4.
These are central-site values, NOT total particle number or whole-lattice errors.

The saved Heisenberg operators include the actual native preparation gates
and unmasking signs. We evaluate them on the all-zero input, without a second
preparation, operator renormalization or replacement of the ideal expectation.
The exact F00=1 overlap identity is not a license to rescale these operators.

## Individual Pauli arms

Measured values below have readout correction; +/- is the shared-calibration
bootstrap standard deviation, not a certified confidence bound.

| CZ factor | Shots | Z_up model | Z_up measured | Z_down model | Z_down measured | ZZ model | ZZ measured |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 64 | .491671 | .476074 +/- .112722 | .274025 | .349121 +/- .121168 | .123848 | .257874 +/- .124886 |
| 2 | 7 | .309092 | .145089 +/- .381626 | .253181 | .435268 +/- .346007 | .075286 | .736782 +/- .273358 |
| 3 | 14 | .184149 | -.145089 +/- .270278 | .217298 | .290179 +/- .261057 | .039540 | -.294713 +/- .263777 |

For factor2 ZZ, measured-minus-model is +.661495.
Its nominal marginal 95% bootstrap interval is [.066997, .994346].
One of nine Pauli margins excludes the model. This is an unadjusted,
post-hoc diagnostic, NOT a simultaneous significance test or established
model failure. Factor2 spin also flags outside its derived marginal interval;
it is a correlated transformation of the same counts, not independent evidence.
All factor1 and factor3 Pauli and physical margins include their model values.

## Central physical quantities

| CZ factor | Charge model | Charge measured | Spin model | Spin measured | D model | D measured |
|---|---:|---:|---:|---:|---:|---:|
| 1 | .617152 | .587402 | -.108823 | -.063477 | .089538 | .108170 |
| 2 | .718864 | .709821 | -.027956 | .145089 | .128253 | .289106 |
| 3 | .799276 | .927455 | .016574 | .217634 | .159523 | .140050 |

For factor1, measured SDs are .087301, .077926 and .039691 respectively.
Full intervals and cross-arm covariance are saved in summary.json.
All four model arms, including the ideal one, give valid reconstructed
central two-mode joint probabilities at this numerical tolerance.
No point estimates, bootstrap tails or probabilities were clipped.

## Ideal TN versus exact finite-circuit reference

| Central quantity | Saved ideal TN | Exact circuit | TN minus exact |
|---|---:|---:|---:|
| Z_up | .956628930 | .957350560 | -.000721629 |
| Z_down | .235773733 | .233308190 | +.002465543 |
| ZZ | .237676227 | .229400442 | +.008275785 |
| Charge | .403798668 | .404670625 | -.000871957 |
| Spin | -.360427599 | -.362021185 | +.001593586 |
| D | .011318391 | .009685423 | +.001632968 |

The ideal saved means are much closer to this reference than the hardware
point errors in the parent mitigation test. That is encouraging for this
specific input and central site, but not a general TN error bound or proof
that all noisy-channel truncation errors are small.

The reference is the exact FINITE CIRCUIT, not automatically exp(-i H T);
product-formula error is a separate question. The earlier raw ZZ Gram
change still fails its 1% criterion (1.31%). Its exact-norm/G/b local checks
pass, but that does not erase the raw failure or certify observable errors.

## Exposure, uncertainty and inference limits

This arm-level check uses all 64/7/14 archived target shots (85 total) plus
the same 128 calibration shots (64 all-zero and 64 all-one). The selected
union is 213 shots; no new shots were collected. It is not a new matched-budget
estimator comparison: that earlier L-MPF/ZNE primary comparison uses 43/7/14.

We exactly reuse all 10,000 paired bootstrap draws from the parent:
shared Beta calibration draws first, then the predefined 43/21/7/14
multinomial strata. Factor1 is the sum of the saved 43+21 draws.
The two measured bits and all arm-to-arm calibration correlations are retained.
Unobserved outcomes remain unobserved in the empirical bootstrap, an especially
important limitation at seven shots. Intervals are marginal and heuristic;
model bias, TN bias, calibration drift, coherent errors and correlated readout
are not included. Compatibility with a wide interval is not model validation.

No target means or reference were used to fit noise rates or select a model.
The model remains the archived gate-error local-depolarization surrogate.
Its 12 predictions were saved before observed means were compared, but this
is still post-hoc analysis of reused data, not a new held-out experiment.

## Execution and reproducibility

Current main calculation: 24.266247 s; independent audit: 6.296220 s
(excluding their Python startup). 84 tests passed, all 12 raw-TN contractions
and all 10,000 bootstrap draws independently checked. Maximum contraction
difference: 8.33e-16; maximum replay discrepancy: 1.23e-15.
No QPU use or fresh TN propagation. Prior operator-preparation cost is not
included and these timings are not a quantum/classical advantage comparison.

The first attempt's numerical output completed in 25.549306 s, but its
independent verifier stopped on a string-versus-integer JSON key error.
That attempt and its frozen sources are preserved in the sibling v1 folder.
The corrected v2 adds a regression test; both arm_bootstrap.npz files have
identical SHA256 8b15c8391ce311a8669faef464fb488cd81fb7dc2ed215a8cb3e6691963be550.
Both attempts plus the audits stayed within the 120-second local numerical
execution allowance; coding, file review and Git archival take separate time.

Reproduce into a NEW output folder; the programs refuse existing deliveries:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 timeout --signal=KILL 120s \
  /home/bram/.venvs/qiskit/bin/python -B lmpf_2d/twirl1_noise_check.py \
  --output results_cuprate_2d/lmpf_3x3_twirl1_noise_model_reproduction
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 timeout --signal=KILL 45s \
  /home/bram/.venvs/qiskit/bin/python -B lmpf_2d/verify_twirl1_noise_check.py \
  results_cuprate_2d/lmpf_3x3_twirl1_noise_model_reproduction
```

See VERIFICATION.md for executed audit evidence and NEXT_SMALL_SAMPLE_CHECK.md
for the prepared, not executed follow-up. No hardware or publication is authorized.
