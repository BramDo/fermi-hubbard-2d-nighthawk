# Exploratory relaxed-filter TFLO: existing data only

Source job: dae3rou42tqs73au78d0; new QPU usage: 0 seconds.
The original failed strict-filter analysis remains unchanged. This is not a fresh blinded confirmatory test.

Selected on U=0 ONLY: tflo_k1; tolerance 1.
The six training settings fit the coefficients; the two separate U=0 holdout times select the filter.
U=8 data and references were excluded from that choice and fitting; no physical clipping.

| Candidate | Feasible | U=0 holdout Pauli MSE |
|---|---|---:|
| raw | True | 0.313132 |
| tflo_k18 | True | 0.004051 |
| tflo_k4 | True | 0.004121 |
| tflo_k3 | True | 0.005153 |
| tflo_k2 | True | 0.004354 |
| tflo_k1 | True | 0.003747 |
| tflo_k0 | False | not fitted |

| U=8 time | Retained | Method | Charge RMSE | Spin RMSE | Doublon RMSE |
|---|---:|---|---:|---:|---:|
| 0.2 | 176 | raw | 0.1840 | 0.5829 | 0.1725 |
| 0.2 | 176 | postselected | 0.1869 | 0.5569 | 0.1408 |
| 0.2 | 176 | corrected | 0.0236 | 0.0745 | 0.0164 |
| 0.4 | 157 | raw | 0.1572 | 0.4792 | 0.1323 |
| 0.4 | 157 | postselected | 0.1372 | 0.4594 | 0.1103 |
| 0.4 | 157 | corrected | 0.0489 | 0.2047 | 0.0599 |

Pooled U=8 Pauli MSE: raw=0.318025; corrected=0.030717.
Paired raw-minus-corrected MSE gain, 95% bootstrap interval WITH U=0 filter reselection: {'low': 0.26954485622832514, 'high': 0.31091887502506627, 'valid_replicates': 400}.
Bootstrap selections: {'tflo_k2': 59, 'tflo_k4': 107, 'tflo_k3': 44, 'tflo_k18': 94, 'tflo_k1': 95, 'tflo_k0': 1}; failures: {'locked': 0, 'reselected': 0}.

Intervals exclude systematic transfer bias and do not establish quantum advantage or calibrated future-circuit fidelity.
The cleaner compiled circuits were NOT run on hardware. Their performance cannot be inferred as a measured result from this reanalysis.
