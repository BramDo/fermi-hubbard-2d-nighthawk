# 2D Cuprate Layout Scout

Dry-run only. No IBM Runtime, Fire Opal, or hardware jobs were submitted.

## Backend

- backend: `ibm_phoenix`
- pending_jobs: 0
- operational: True

## Best Candidate

- candidate: `sabre_seed_9`
- seed_transpiler: `9`
- score: `4.025581762663888`
- depth: `249`
- two_qubit_depth: `89`
- two_qubit_count: `777`
- edge_error_sum: `2.802140030893055`
- readout_error_mean: `0.009080674913194444`
- readout_error_max: `0.0384521484375`
- recommended runner seed: `9`
- force initial_layout by default: `False`
- runner note: For Qiskit SABRE candidates, reproducing the best seed is the first choice. Forcing the discovered physical map as initial_layout can change routing and should be rescored.

## Top Candidates

| rank | candidate | seed | score | 2q count | 2q depth | readout mean | edge error sum |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | sabre_seed_9 | 9 | 4.025582 | 777 | 89 | 0.009081 | 2.802140 |
| 2 | sabre_seed_3 | 3 | 4.367129 | 768 | 96 | 0.009221 | 3.129966 |
| 3 | sabre_seed_8 | 8 | 5.111991 | 795 | 95 | 0.009038 | 3.868820 |
| 4 | sabre_seed_2 | 2 | 5.174925 | 702 | 80 | 0.009118 | 4.005865 |
| 5 | sabre_seed_1 | 1 | 5.265093 | 804 | 99 | 0.010273 | 3.590315 |
| 6 | sabre_seed_7 | 7 | 5.568799 | 804 | 113 | 0.009839 | 3.879042 |
| 7 | sabre_seed_10 | 10 | 6.007565 | 729 | 88 | 0.010544 | 4.384149 |
| 8 | sabre_seed_6 | 6 | 6.092486 | 819 | 101 | 0.010540 | 4.398172 |
| 9 | sabre_seed_12 | 12 | 6.631921 | 795 | 88 | 0.010737 | 4.969707 |
| 10 | sabre_seed_4 | 4 | 6.892333 | 825 | 114 | 0.010349 | 5.174765 |

Claim boundary: this ranks compilation/calibration diagnostics only. A selected layout still needs a gated hardware submission and baseline comparison.
