# One hardware pilot: readout + native CZ-folding ZNE

User authorization: "laten we dan maar hardware runs doen met reedout + ZNE CZ folding".
Interpretation: begin with ONE job under the previously agreed 5-QPU-second cap.
No automatic repetition, backend replacement, budget increase, PEC, PEA or TFLO.
Backend ibm_phoenix (Nighthawk), named account qiskit-runtime-q9. No session/batch.
This authorization is separate from all previous consumed hardware job locks.

## Frozen experiment

Same 3x3,18 spinful modes,U/t=8,T=0.4,two Trotter steps,t'=-0.25,
Nup=Ndown=4 and original eight physical layouts/masks/twirls from the Aer study.
One common physical layout is retained for all circuits; no retranspilation.
Import the already validated CZ-folded18-wire QPY circuits, embed into their
original120-wire device mapping, verify inverse mapping and noise-off reference.
Factors1,2,3 have1008,2016,3024 CZ gates, respectively. CZ^3=CZ; factor2
folds half of each ordered support. Only the CZ exposure is amplified.
Native X/SX noise, readout, drift and other unmodelled errors are not uniformly scaled.

26 scalar Sampler PUBs: two calibration circuits and24 factor/twirl circuits.
Calibration all-zero/all-one:64 shots each, prepared on the same18 wires.
Both calibrations are adjacent at the start. Remaining24 PUBs are shuffled
once with seed2026090607; frozen before any provider submission.
Hardware execution order beyond input order is provider-controlled.
Factor1:8x64=512; factor2:8x7=56; factor3:8x14=112. Total NEW shots808.
Readout calibration includes SPAM preparation error and is not perfect truth.

| Analysis arm | Selected target shots | Calibration | Total |
|---|---:|---:|---:|
| Raw | 512 factor1 | 0 | 512 |
| Readout only | 384 factor1 | 128 | 512 |
| Readout + ZNE PRIMARY | 216/56/112 at factors1/2/3 | 128 | 512 |

Raw and ZNE share the first27 factor1 shots per twirl; readout-only uses
first48. Remaining factor1 shots are preserved as raw-control data.
Linear intercept weights[4/3,1/3,-2/3], allocation[27,7,14] per twirl,
same as the completed Aer readout pilot. Do not choose an extrapolator after
seeing data. ZNE without readout is a paired diagnostic, not an optimized arm.
Readout-only384 and raw512 have387072 and516096 CZ applications;
readout+ZNE has669312. Total physically sampled CZ applications967680.
Equal analytical shot budgets do not imply equal gate, timing or billing cost.

## Analysis fixed before hardware

Use the tested local inverse-moment readout correction, not M3 or TREX software.
e0/e1 are independently estimated per physical wire with Jeffreys mean
(error_count+.5)/65. For decoded Z and mask m, a=(-1)^m(e1-e0), b=1-e0-e1:
Zcorrected=(Z-a)/b and ZZcorrected=(ZZ-a_u Z_d-a_d Z_u+a_u a_d)/(b_u b_d).
Refuse b<=.2; no clipping, filtering, postselection or fitted scale against U8 truth.
Z=1-2n; spin=nup-ndown, not Sz; doublon=nup*ndown. All reported values dimensionless.
Exact reference is the SAME finite Trotter circuit, not exact continuous dynamics.

Primary endpoint: raw512 spin-RMSE minus readout+ZNE spin-RMSE.
Lading/charge and doublon RMSE, Pauli MSE, absolute particle-number deviation,
physical local probabilities and Pauli bounds are mandatory guardrails.
Report all native factor values and all sites, even if the mitigation fails.
2000 fixed-twirl paired bootstrap replicates, seed2028600000.
Factor1 strata27/21/16 preserve all overlaps; factor2 and3 resampled separately.
Whole-shot vectors preserve correlations between Z/ZZ and sites. One shared
Beta(count+.5,64-count+.5) calibration draw per replicate for every arm.
Report hybrid95% bootstrap/calibration-posterior intervals, not coverage-certified
frequentist confidence intervals. Also fixed-calibration bootstrap and200/1000/2000
replicate quantiles. Drift, correlated/SPAM bias and extrapolation bias are not covered.
With8 twirls this is a small pilot, not an accuracy certificate or advantage claim.

## Safety and budget gate

Before POST: unit tests;24 ideal folded-circuit checks;26 QPY round trips;
live backend operational status; target ISA and faulty-gate checks; frozen input
hashes; same instance fingerprint; current default rep_delay (never lowered);
two independent circuit duration calculations and reset overhead included.
Estimate one/two/three internal subjobs with approximately2s overhead each.
Require the two-subjob scenario below5s. Actual subjob splitting is unknown;
the estimate is not a guaranteed bill or guaranteed completion.
Set max_execution_time=5 on the job; verify the provider's returned cap field.
Disable built-in twirling/DD because circuits already contain the explicit twirls.
Transport retries disabled before Sampler.run. Exactly one durable atomic lock
is created BEFORE POST. On an ambiguous outcome, recover only by the unique tag.
Never delete the lock, create an alternate output directory to resubmit, or retry POST.
The backend may cancel at the time limit; an incomplete result must not be used
as if the whole plan completed. Failed/cancelled jobs may consume QPU time.

Retrieve only the existing job. Preserve provider metrics, options, actual QPY,
raw Runtime result, every measured bitstring and all calibration counts.
Verify actual provider circuit/PUB/shot/metadata ordering against frozen intent.
Never write or display tokens, full CRNs or raw provider exception messages.

Sources:
https://quantum.cloud.ibm.com/docs/en/guides/max-execution-time
https://quantum.cloud.ibm.com/docs/en/guides/estimate-job-run-time
