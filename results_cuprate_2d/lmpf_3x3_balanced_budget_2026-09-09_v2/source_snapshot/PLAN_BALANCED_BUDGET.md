# Before-run protocol: offline 3x3 balanced-shot and QPU-time budget

Scope: central twirl1 transfer-test planning only, same archived native
circuits from job daem7r642tqs73autong on ibm_phoenix. No cloud connection,
submission, new operator states, noise fitting or publication. Up to120s local.

Compare n=64,128,256,512 target shots per folded factor. Calibration m=256
per all-zero/all-one state for every case. Primary readout-only baseline
gets3n factor1 shots, while ZNE/L-MPF each get n+n+n=3n. The shared factor1
subset is n, extra baseline-only2n. Union5n+512 shots; do not count shared
data twice. Plan interleaved fixed blocks, not target-dependent resampling.

## Equation registry

All moments, probabilities and errors are dimensionless; durations in seconds.

- Raw readout probabilities q_a come from the archived frozen noisy operator
  means and the saved readout error probabilities e (assumed truth for planning).
  No old target frequencies or exact reference enter the forecast.
- A future Jeffreys error estimate is (K+.5)/(m+1), K~Binomial(m,e).
  Expansion center e_bar=(m*e+.5)/(m+1), Var(e_hat)=m*e*(1-e)/(m+1)^2.
  Four independent single-bit calibration-error coordinates are assumed.
- Moment score h_o(x,e_bar,mask) is the established inverse-readout/unmask
  function. Conditional per-shot covariance S=E[h h^T]-E[h]E[h]^T,
  with the full two-bit joint model q. Code: score covariance.
- Shot-aware L-MPF uses unchanged eta1 and the archived high/low Grams,
  with diagonal penalty P_oa=(range h_o)^2/(4n), constraint sum_a c_oa=1.
  Recompute coefficients for EACH shot budget before target data exist.
  Code: existing variance_penalties / solve_weights. Preserve low/high L1
  changes and their previous .05 local threshold; no automatic validation.
- Linear ZNE coefficients stay [4/3,1/3,-2/3]; readout/raw baselines are3n.
  Convert moments via L=[[-.5,-.5,0],[-.5,.5,0],[-.25,-.25,.25]],
  offset=(1,0,.25), giving central charge, spin=n_up-n_down, D.
- Build one joint12x12 covariance for raw/RO/ZNE/L-MPF x3 physical quantities
  using the four independent strata[n,2n,n,n]. This preserves shared shots.
- Add FIRST-ORDER calibration covariance J diag(Var(e_hat)) J^T, where J
  differentiates expected output at FIXED model q, including weight dependence.
  Production central differences h=1e-5 and5e-6 must agree; independent audit
  uses complex-step derivatives and a separate constrained KKT solve.
  This delta approximation omits higher-order/mixed terms, model bias, TN
  uncertainty, drift, coherent noise and correlated readout. It is NOT a
  confidence interval or guaranteed hardware accuracy.
- Paired difference variance uses the full shared covariance, not an
  independence assumption. Record projected means as MODEL FORECASTS only.

## Timing equations and frozen evidence

Read the five exact provider QPYs at indices[0,1,25,19,2] (cal0/cal1/f1/f2/f3).
Check against archived hashes/bound QPYs and the parent operator binding.
Reconstruct their ASAP critical paths from archived physical gate/readout
lengths, converting ns/us to seconds. Verify against saved dispatch timings
and independently with a Qiskit Target constructed from the same snapshot.

E(n)=3n(t1+reset+rep)+n(t2+reset+rep)+n(t3+reset+rep)
     +m(tcal0+reset+rep)+m(tcal1+reset+rep).

Historical reset=.4us and rep=1us; these are not a live backend guarantee.
Also report a250us rep-delay sensitivity (generic scenario, not its current
default). A shorter rep_delay can increase preparation error; no speed
recommendation may silently change it.

IBM's public workload-usage documentation, checked2026-09-09:
https://quantum.cloud.ibm.com/docs/en/guides/estimate-job-run-time
Baseline approximation is approximately2s overhead per internal sub-job,
plus circuit execution/repetition time. Give1/2/3-subjob scenarios, not an
invoice guarantee. Circuit execution time is NOT charge time or wall time.

Keep the historical full-job measurements separate:
808 shots, local execution estimate .018469216s,
provider circuits_execution_time_ns=24533248 and usage3s.
Do NOT scale3s linearly by the new shot count. Report the difference between
local and provider execution as a sensitivity warning, not a new fitted
noise model or established timing calibration.

## Tests and decision boundary

Expect tens to hundreds of milliseconds of shot execution at these budgets,
with approximately seconds of overhead. Sample SD should fall roughly as
1/sqrt(n) only for FIXED weights and negligible calibration floor. New
shot-aware weights may change this trend, so do not force monotonicity.

Tests: masked zero/asymmetric readout, weighted categorical covariance and
shared-mean difference variance, finite/complex-step derivative agreement,
fixed-weight1/sqrt(n), KKT normalization/residual, unit conversions and
nontrivial parallel circuit timing. Verify all four full covariance matrices,
paired differences, weight changes, exposure accounting and timing independently.

A suggested candidate can be the largest of the fixed n choices with passing
archived local coefficient flags and a two-subjob estimate within5s, with
the250us sensitivity also disclosed. This is an OFFLINE planning rule, not
authorization or a claim that the bill will fit. If the local flag fails,
keep the failed result and stop short of recommending its L-MPF execution.

Before any submission: user chooses backend, exact shots and hard cap;
fresh live ISA/fault/calibration compatibility and quota/budget checks are
needed. Old5s/15s approvals do not apply. No retry or6x6 escalation.
