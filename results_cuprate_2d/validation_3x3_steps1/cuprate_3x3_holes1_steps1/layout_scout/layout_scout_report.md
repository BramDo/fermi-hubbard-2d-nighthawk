# 2D Cuprate Layout Scout

Dry-run only. No IBM Runtime, Fire Opal, or hardware jobs were submitted.

## Backend

- backend: `ibm_marrakesh`
- pending_jobs: 8
- operational: True

## Best Candidate

- candidate: `sabre_seed_47`
- seed_transpiler: `47`
- score: `11.230449639898207`
- depth: `4053`
- two_qubit_depth: `1740`
- two_qubit_count: `2946`
- edge_error_sum: `6.031884861252374`
- readout_error_mean: `0.004645453559027778`
- readout_error_max: `0.0106201171875`
- recommended runner seed: `47`
- force initial_layout by default: `False`
- runner note: For Qiskit SABRE candidates, reproducing the best seed is the first choice. Forcing the discovered physical map as initial_layout can change routing and should be rescored.

## Top Candidates

| rank | candidate | seed | score | 2q count | 2q depth | readout mean | edge error sum |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | sabre_seed_47 | 47 | 11.230450 | 2946 | 1740 | 0.004645 | 6.031885 |
| 2 | sabre_seed_48 | 48 | 11.355404 | 2937 | 1849 | 0.004381 | 6.003764 |
| 3 | sabre_seed_44 | 44 | 11.592958 | 2886 | 1937 | 0.004327 | 6.092445 |
| 4 | sabre_seed_12 | 12 | 12.165640 | 3009 | 1926 | 0.004279 | 6.629493 |
| 5 | sabre_seed_20 | 20 | 18.285070 | 2778 | 1776 | 0.004157 | 13.168086 |
| 6 | sabre_seed_50 | 50 | 50.397171 | 2937 | 1852 | 0.004476 | 45.036683 |
| 7 | sabre_seed_43 | 43 | 55.892529 | 2895 | 1873 | 0.004476 | 50.511040 |
| 8 | sabre_seed_42 | 42 | 56.954458 | 2916 | 1747 | 0.004469 | 51.814673 |
| 9 | sabre_seed_29 | 29 | 70.588649 | 2868 | 1911 | 0.004476 | 65.144661 |
| 10 | sabre_seed_36 | 36 | 76.267424 | 2895 | 1870 | 0.004469 | 70.892139 |

Claim boundary: this ranks compilation/calibration diagnostics only. A selected layout still needs a gated hardware submission and baseline comparison.
