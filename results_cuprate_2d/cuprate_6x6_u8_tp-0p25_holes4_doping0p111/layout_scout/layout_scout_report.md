# 2D Cuprate Layout Scout

Dry-run only. No IBM Runtime, Fire Opal, or hardware jobs were submitted.

## Backend

- backend: `ibm_marrakesh`
- pending_jobs: 8
- operational: True

## Best Candidate

- candidate: `sabre_seed_46`
- seed_transpiler: `46`
- score: `296.14949274520114`
- depth: `42571`
- two_qubit_depth: `19517`
- two_qubit_count: `42102`
- edge_error_sum: `235.44330744246676`
- readout_error_mean: `0.009190877278645834`
- readout_error_max: `0.0345458984375`
- recommended runner seed: `46`
- force initial_layout by default: `False`
- runner note: For Qiskit SABRE candidates, reproducing the best seed is the first choice. Forcing the discovered physical map as initial_layout can change routing and should be rescored.

## Top Candidates

| rank | candidate | seed | score | 2q count | 2q depth | readout mean | edge error sum |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | sabre_seed_46 | 46 | 296.149493 | 42102 | 19517 | 0.009191 | 235.443307 |
| 2 | sabre_seed_44 | 44 | 398.441504 | 42240 | 19047 | 0.016507 | 333.317266 |
| 3 | sabre_seed_10 | 10 | 544.868590 | 41172 | 20435 | 0.016030 | 477.516645 |
| 4 | sabre_seed_39 | 39 | 722.982472 | 42147 | 21385 | 0.009259 | 658.556035 |
| 5 | sabre_seed_9 | 9 | 739.253904 | 41760 | 18831 | 0.009254 | 680.042450 |
| 6 | sabre_seed_31 | 31 | 757.918032 | 42384 | 18383 | 0.008582 | 699.487722 |
| 7 | sabre_seed_49 | 49 | 835.260618 | 41997 | 19257 | 0.011214 | 775.106536 |
| 8 | sabre_seed_8 | 8 | 855.933066 | 42114 | 20548 | 0.023980 | 788.227901 |
| 9 | sabre_seed_18 | 18 | 990.250766 | 42240 | 19465 | 0.011424 | 929.552878 |
| 10 | sabre_seed_38 | 38 | 1065.055556 | 41697 | 18977 | 0.009762 | 1005.706283 |

Claim boundary: this ranks compilation/calibration diagnostics only. A selected layout still needs a gated hardware submission and baseline comparison.
