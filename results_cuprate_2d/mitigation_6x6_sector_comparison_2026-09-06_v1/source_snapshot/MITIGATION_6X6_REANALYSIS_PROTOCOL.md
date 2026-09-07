# 6x6 mitigation comparison: offline follow-up

Scope: existing job daen2vdnj4cs73afcn00 only; zero new QPU seconds. No submit,
credentials, backend lookup, package install, alteration of frozen archives,
or reuse of old hardware authorization. This is exploratory reanalysis:
previous U=8 results and sector acceptance counts have already been inspected.

## Target and conventions

6x6 open-boundary t-t-prime-U Hubbard, t=1, t-prime=-0.25, U=8,
T=0.4 in units hbar/t, two symmetric steps, four holes, 72 modes.
Little-endian interleaved modes q(2i)=up, q(2i+1)=down after undoing the
recorded readout-X masks. N_up=N_down=16. Charge=n_up+n_down,
spin=n_up-n_down (NOT physical S_z=spin/2), doublon=n_up*n_down.
All reported observables are dimensionless. Compare exactly these site
profiles with the saved chi=64 finite-circuit MPS, NOT an exact reference.
Its chi=32-to-64 disagreement remains a separate convergence limitation.

## Equations and fixed analysis

| Equation | Implementation |
|---|---|
| P=1[N_up=16 and N_down=16] | strict_success |
| O=(n_up+n_down,n_up-n_down,n_up*n_down) | site_samples |
| conditional mean = mean(P O)/mean(P) | projected |
| ZNE+projection = sum_f w_f mean_f(P O)/sum_f w_f mean_f(P) | projected |
| w=(4/3,1/3,-2/3), factors 1,2,3 | WEIGHTS |
| RMS discrepancy=sqrt(mean_sites((estimate-MPS)^2)) | summarize |

Compare saved raw, readout, readout+CZ-ZNE with strict sector postselection
at factor 1, and an explicitly exploratory CZ-ZNE+sector ratio. The latter
extrapolates UNNORMALIZED numerator and denominator before taking the ratio;
it does not simply extrapolate conditionally normalized point estimates.
The new sector arms do NOT include independent readout inversion. Applying
the original unconditional per-qubit correction after measured-sector
selection is not generally a valid combined estimator. No such shortcut.
No filter relaxation, clipping, learned fit, or MPS-targeted parameter tuning.

Each factor has eight fixed twirls x 512 shots. Pool shots within factors;
after selection this is explicitly acceptance-weighted across twirls.
Bootstrap whole shots independently within each original PUB, retaining
reject events. This propagates random acceptance counts and denominator
uncertainty. Fixed 2000 replicas and seed 202609060913. Compare first 1000
with 2000 replicas as a bootstrap Monte Carlo stability diagnostic, not
additional physical sample convergence. If the extrapolated success
denominator interval crosses zero, do not publish a finite ratio interval.
Retain actual counts and per-twirl diagnostics; force N=32 is not validation.

The old baseline hybrid bootstrap includes independent-channel calibration
uncertainty. The new sector arms include shot noise at fixed twirls, but
NOT calibration correction, drift, correlated readout, postselection bias,
extrapolation bias, MPS truncation, or Trotter error. Baseline/new arm
intervals are not interchangeable total-error certificates. Shot budgets
differ; no equal-budget or advantage claim. Paired raw-to-sector diagnostic
uses fresh matched bootstrap draws, without selecting a winner by that test.

## Expectations and verification fixed before new observable calculation

Counts already inspected: accepted factor 1/2/3 = 48/46/45 out of 4096 each.
Expect N=32 identically after selection, but this alone cannot restore
spin contrast. Flat/noisy spin may remain roughly 0.7 RMS from chi=64.
The ratio can be noisy and nonphysical even when each selected bitstring
is physical. Save unmodified estimates and physical-bound diagnostics.

Tests: bit-endianness/mask inversion; hand-computed two-site observables;
strict spin-sector vs total-number distinction; empty-sector rejection;
zero-noise identity; synthetic linear numerator/denominator extrapolation;
independent integer popcount and direct bit-feature computation for real
records; unchanged input hashes before/after; reproduce archived raw and
readout+ZNE point estimates. Save all code, results, bootstrap samples and
verification evidence to a NEW sibling directory.

## What cannot be applied to these saved data

DD requires pulses during a NEW hardware run. TFLO requires matching 6x6
U=0 hardware training and independent held-out controls. The available
3x3 TFLO fit and 5x5 U=0 control are not interchangeable with 6x6 U=8.
MESR requires separately validated corrected constraints, not MPS answers
inserted into the hardware results. No PEC noise model is present here.

Next hardware proposal, not authorization: same 6x6 target, matched layout,
identical compiled gate skeleton for U=0 and U=8, readout/twirling retained,
DD on/off paired arms and separate U=0 training/holdout circuits; report
U=8 versus raw and a purely classical U=0 comparator. Do not change circuit
and mitigation together in a claimed causal A/B comparison. Fresh budget
estimate and explicit capped one-job approval required before submission.

Primary source: https://arxiv.org/html/2510.26845v2, Methods: Error mitigation.
Its performance is not a guarantee for this hardware or this Hamiltonian.
