# 2D Cuprate Layout Scout

Dry-run only. No IBM Runtime, Fire Opal, or hardware jobs were submitted.

## Backend

- backend: `ibm_marrakesh`
- pending_jobs: 7
- operational: True

## Best Candidate

- candidate: `sabre_seed_26`
- seed_transpiler: `26`
- score: `14.151933016531185`
- depth: `367`
- two_qubit_depth: `138`
- two_qubit_count: `1164`
- edge_error_sum: `12.65748892473431`
- readout_error_mean: `0.011530558268229166`
- readout_error_max: `0.029052734375`
- recommended runner seed: `26`
- force initial_layout by default: `False`
- runner note: For Qiskit SABRE candidates, reproducing the best seed is the first choice. Forcing the discovered physical map as initial_layout can change routing and should be rescored.

## Top Candidates

| rank | candidate | seed | score | 2q count | 2q depth | readout mean | edge error sum |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | sabre_seed_26 | 26 | 14.151933 | 1164 | 138 | 0.011531 | 12.657489 |
| 2 | sabre_seed_20 | 20 | 14.803322 | 1023 | 105 | 0.011531 | 13.445378 |
| 3 | sabre_seed_28 | 28 | 16.398960 | 1068 | 121 | 0.010361 | 15.021611 |
| 4 | sabre_seed_16 | 16 | 18.136236 | 1035 | 129 | 0.011531 | 16.724292 |
| 5 | sabre_seed_32 | 32 | 18.994001 | 1038 | 134 | 0.011531 | 17.570557 |
| 6 | sabre_seed_3 | 3 | 19.290019 | 1059 | 120 | 0.011353 | 17.889415 |
| 7 | sabre_seed_44 | 44 | 19.346438 | 990 | 96 | 0.011531 | 18.022994 |
| 8 | sabre_seed_5 | 5 | 19.806469 | 1086 | 139 | 0.011531 | 18.349025 |
| 9 | sabre_seed_30 | 30 | 20.367825 | 1092 | 168 | 0.010361 | 18.884476 |
| 10 | sabre_seed_13 | 13 | 20.376214 | 1110 | 145 | 0.011334 | 18.900670 |

Claim boundary: this ranks compilation/calibration diagnostics only. A selected layout still needs a gated hardware submission and baseline comparison.
