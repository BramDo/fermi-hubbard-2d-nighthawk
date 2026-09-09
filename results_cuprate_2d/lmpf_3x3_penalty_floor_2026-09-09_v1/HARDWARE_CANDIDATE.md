# Draft independent hardware transfer test:3x3,512 shots, cap64

Status: PREPARED ONLY. NO AUTHORIZATION, NO SUBMISSION.
Backend candidate: ibm_phoenix. Proposed maximum execution time5 QPU seconds.
No inherited5s/15s approval is valid for this new test.

## Frozen target and data allocation

3x3 spinful Hubbard,18 active modes,N8,U8,t1,t'=-.25,T=.4,
two symmetric steps, original explicit twirl1 and physical layout from
the archived3x3 job. Reuse exact native provider circuit content at
indices25/19/2 for factors1/2/3, and0/1 for readout calibration.
No recompilation, backend replacement or circuit changes without review.

Twenty planned PUBs, fixed before new outcomes:
- Pre-calibration: all0/all1,128 shots each.
- Four blocks, each: shared factor1=128, factor2=128,
  baseline-only factor1=256, factor3=128.
- Post-calibration: all0/all1,128 shots each.

Totals: factor1=1536, factor2=512, factor3=512, calibration512,
data union3072. Each main corrected estimator has1536 target+512 calibration
shots. The floor/ZNE factor1 estimate MUST use only the512 designated shared
shots; readout-only uses all1536. No outcome-dependent subset selection.

## Analysis rule and holdout boundary

Readout inverse and masks follow the established two-bit assignment convention.
Combine the256 shots per prepared calibration state with a Jeffreys estimator,
also report pre/post calibration differences. Extreme inverse conditioning
or failing low/high coefficient checks must be reported, not hidden.

Primary L-MPF penalty denominator64, eta1, same archived high/low Grams;
actual shot count512 per factor. Recompute weights from calibration only,
freeze them before scoring target outcomes. No exact-reference or target
training, postselection, clipping or fitting of a new noise rate.
Linear ZNE stays[4/3,1/3,-2/3]. Keep readout-only/raw and original1/n L-MPF
as predeclared comparisons, not alternative primary results to select afterward.

Report central charge/spin/D, all local probabilities and paired uncertainty.
Use10000 stratified bootstrap replicates, seed2026090922, retaining shared
shots and shared calibration and recomputing calibration-dependent weights.
After weights are frozen, compare to the identical exact finite-circuit
reference;95% intervals are descriptive, not an automatic advantage claim.
Do not pool the new targets with old exploratory data as the primary result.

This is a transfer/holdout test of an archived model. Fresh device calibration
or unmodeled drift may change the result. Passing the offline screen is not
validation of the new hardware, all sites, longer dynamics or6x6.

## Submission gates (all still pending)

1. Fresh explicit user approval of backend,3072 total shots and5s cap.
2. Read-only live backend/quota/fault/ISA/timing compatibility check.
3. Keep runtime gate/measurement twirling and DD off; manual twirl1 stays fixed.
   Archived init_qubits=true and rep_delay=1us require a fresh allowed-range
   check; if incompatible, stop rather than silently change options.
4. Freeze hashes, complete PUB manifest and analysis rule; run offline safety
   tests before any dispatch. Record a single attempt marker and receipt.
5. One job only, no automatic retry. If an uncertain dispatch occurs, resolve
   the existing attempt; do not resubmit. No budget increase or6x6 follow-up.
6. Preserve every raw result, usage/timestamps, failure and calibration record.
   No publishing or pushing without separate approval.

Archived timing is a scenario only. One/two subjobs give about2.08/4.08s
at the old rep_delay; three subjobs exceed6s and can hit the proposed cap.
A5s cap limits the requested workload but cannot promise complete results.
