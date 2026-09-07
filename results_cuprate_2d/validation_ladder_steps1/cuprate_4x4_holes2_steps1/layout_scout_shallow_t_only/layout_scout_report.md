# 2D Cuprate Layout Scout

Dry-run only. No IBM Runtime, Fire Opal, or hardware jobs were submitted.

## Backend

- backend: `ibm_marrakesh`
- pending_jobs: 6
- operational: True

## Best Candidate

- candidate: `sabre_seed_3`
- seed_transpiler: `3`
- score: `1.7030791797838467`
- depth: `199`
- two_qubit_depth: `65`
- two_qubit_count: `341`
- edge_error_sum: `1.188422075291659`
- readout_error_mean: `0.00485992431640625`
- readout_error_max: `0.0068359375`
- recommended runner seed: `3`
- force initial_layout by default: `False`
- runner note: For Qiskit SABRE candidates, reproducing the best seed is the first choice. Forcing the discovered physical map as initial_layout can change routing and should be rescored.

## Top Candidates

| rank | candidate | seed | score | 2q count | 2q depth | readout mean | edge error sum |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | sabre_seed_3 | 3 | 1.703079 | 341 | 65 | 0.004860 | 1.188422 |
| 2 | sabre_seed_27 | 27 | 1.734702 | 356 | 69 | 0.004768 | 1.207291 |
| 3 | sabre_seed_36 | 36 | 1.776561 | 365 | 84 | 0.004768 | 1.214651 |
| 4 | sabre_seed_50 | 50 | 1.782174 | 365 | 74 | 0.004768 | 1.240263 |
| 5 | sabre_seed_5 | 5 | 1.834008 | 377 | 81 | 0.004860 | 1.269351 |
| 6 | sabre_seed_6 | 6 | 1.834380 | 368 | 87 | 0.004768 | 1.264969 |
| 7 | sabre_seed_19 | 19 | 1.839373 | 380 | 82 | 0.004860 | 1.271215 |
| 8 | sabre_seed_23 | 23 | 1.850033 | 377 | 88 | 0.004814 | 1.272749 |
| 9 | sabre_seed_30 | 30 | 1.872995 | 380 | 78 | 0.004860 | 1.312838 |
| 10 | sabre_seed_2 | 2 | 1.879611 | 389 | 79 | 0.004845 | 1.308529 |

Claim boundary: this ranks compilation/calibration diagnostics only. A selected layout still needs a gated hardware submission and baseline comparison.
