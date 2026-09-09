# Fresh 3x3 floor64 hardware result

## Outcome

The one authorized job completed and all 3,072 shots were retrieved and verified.
IBM charged **3 QPU seconds**, below the provider-confirmed 5-second maximum.
The independent numerical audit passes, but **general hardware-accuracy
improvement is not established and this result does not support a 6x6 go**.

Job: `dago39b9k43c73adleeg`; backend: `ibm_phoenix`.
No new job, retry, backend switch or budget increase was performed.

## Central-site observables

These are central-site values of the 3x3 spinful Hubbard circuit, not total
particle number or whole-grid averages. Spin is n_up - n_down.
The reference is the exact **finite circuit**, not a certified continuous-time
Hamiltonian evolution. Parameters: t=1, t'=-0.25, U=8, T=0.4, two symmetric
steps, 18 modes, N_up=N_down=4.

| Method | Charge | Spin | Doublon probability |
|---|---:|---:|---:|
| Exact finite circuit | 0.404671 | -0.362021 | 0.009685 |
| Raw | 0.605469 | -0.123698 | 0.094401 |
| Readout only | 0.586292 | -0.136829 | 0.088042 |
| Readout + CZ-folding ZNE | 0.457391 | -0.129251 | 0.033460 |
| Readout + original L-MPF | 0.048388 | -0.218128 | -0.109998 |
| Readout + floor64 L-MPF | 0.255562 | -0.190101 | -0.036401 |

All negative reconstructed probabilities remain visible; nothing was clipped.
The floor64 point estimate still has an unphysical negative doublon probability.
A negative linear-mitigation estimator is not a literal negative physical
probability or, by itself, proof of an implementation bug.

| Absolute error vs exact finite circuit | Charge | Spin | Doublons |
|---|---:|---:|---:|
| Raw | 0.200798 | 0.238323 | 0.084716 |
| Readout only | 0.181621 | 0.225192 | 0.078357 |
| ZNE | 0.052721 | 0.232770 | 0.023775 |
| Original L-MPF | 0.356283 | 0.143893 | 0.119683 |
| Floor64 L-MPF | 0.149109 | 0.171920 | 0.046087 |

ZNE has the smallest point errors for charge and doublons. The original
L-MPF has the smallest point error for spin, but poor charge and a negative
doublon estimate. No method is selected by mixing the best observable from
each result.

## Uncertainty and paired comparisons

The pre-dispatch frozen protocol uses 10,000 paired, 16-stratum target
bootstraps with shared independent Beta readout-calibration draws and refitted
weights, seed 2026090922. The analysis implementation was completed after
submission but before retrieval/scoring of fresh targets. Fits use frozen
overlaps and calibration only; the exact target reference is scoring-only.

| Method | Charge SD | Spin SD | Doublon SD |
|---|---:|---:|---:|
| Readout only | 0.018699 | 0.018213 | 0.007967 |
| ZNE | 0.045707 | 0.045423 | 0.021209 |
| Original L-MPF | 0.104955 | 0.104406 | 0.055551 |
| Floor64 L-MPF | 0.069626 | 0.069744 | 0.035713 |

Floor64 reduces bootstrap SD versus original L-MPF by 33.66%, 33.20% and
35.71%. This is a sampling-spread improvement, not a general accuracy proof.

Floor64 marginal descriptive 95% intervals:
charge [0.119097, 0.392335], spin [-0.326254, -0.052924],
doublons [-0.104958, 0.036193].

Paired improvement is |baseline-reference| - |floor64-reference|;
positive means a smaller absolute error for floor64.

| Baseline | Charge improvement [95% interval] | Spin improvement [95% interval] | Doublon improvement [95% interval] |
|---|---|---|---|
| Readout | 0.032513 [-0.125837, 0.182035] | 0.053272 [-0.069873, 0.170812] | 0.032270 [-0.044661, 0.083342] |
| ZNE | -0.096388 [-0.255920, 0.121087] | 0.060850 [0.002286, 0.115606] | -0.022312 [-0.102182, 0.051148] |
| Original L-MPF | 0.207174 [0.099067, 0.309412] | -0.028027 [-0.104578, 0.077596] | 0.073596 [-0.005673, 0.128110] |

The spin improvement against ZNE and charge improvement against original
L-MPF have positive marginal lower bounds. All readout comparisons include
zero. No baseline is beaten on all three paired intervals. These are not
simultaneous or certified confidence bounds and do not include noise-model,
tensor-network, coherent, drift or correlated-readout bias. Stable coefficients
(point check and all 10,000 calibration draws pass) do not validate those biases.

## Budget and timing

Twenty PUBs: 2,560 target shots plus 512 calibration shots. Readout-only uses
1,536 factor1 targets. ZNE and each L-MPF use the same designated 512 shots
at each factor1/2/3: 1,536 targets each. Each corrected comparison thus uses
2,048 shots including shared calibration; the data union is 3,072.
These are equal-shot comparisons, not equal QPU-time comparisons.

Provider metrics:
- created: 2026-09-09 15:56:21.226196 UTC;
- running: 2026-09-09 15:56:22.132917 UTC;
- finished: 2026-09-09 16:16:11.522465 UTC;
- creation-to-finish: 1,190.296269 seconds (19m50s);
- registered whole-job charge: 3 QPU seconds;
- provider circuits_execution_time_ns: 100042240 (about 0.100s).

These three clocks have different meanings. This run is not a 3-second
end-to-end solution, nor comparable to the historical 6x6 150-second classical
baseline. No quantum advantage is established.

## Evidence and next boundary

See [numerical verification](VERIFICATION.md), [all numerical output](analysis/summary.json),
[provider metrics](provider_metrics.json), [raw shots](raw_bitstrings.json),
and [retrieval checks](retrieval_verification.json). Source/input hashes,
provider circuits, complete results and bootstrap draws are preserved.
Submission-stage documents remain unchanged as historical records.

The next justified investigation is an offline fresh-data/noise-model comparison
and analysis of the spin bias, not automatic 6x6 escalation or another hardware
submission. Any additional QPU run needs fresh explicit authorization.

