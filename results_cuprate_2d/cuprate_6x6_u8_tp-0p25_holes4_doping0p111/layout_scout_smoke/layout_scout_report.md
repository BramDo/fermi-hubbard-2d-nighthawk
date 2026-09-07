# 2D Cuprate Layout Scout

Dry-run only. No IBM Runtime, Fire Opal, or hardware jobs were submitted.

## Backend

- backend: `ibm_marrakesh`
- pending_jobs: 3
- operational: True

## Best Candidate

- candidate: `sabre_seed_2`
- seed_transpiler: `2`
- score: `1128.6784205694892`
- depth: `38597`
- two_qubit_depth: `17850`
- two_qubit_count: `41943`
- edge_error_sum: `1071.2430147263901`
- readout_error_mean: `0.009960598415798612`
- readout_error_max: `0.0465087890625`
- recommended runner seed: `2`
- force initial_layout by default: `False`
- runner note: For Qiskit SABRE candidates, reproducing the best seed is the first choice. Forcing the discovered physical map as initial_layout can change routing and should be rescored.

## Top Candidates

| rank | candidate | seed | score | 2q count | 2q depth | readout mean | edge error sum |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | sabre_seed_2 | 2 | 1128.678421 | 41943 | 17850 | 0.009961 | 1071.243015 |
| 2 | sabre_seed_1 | 1 | 1287.362137 | 42510 | 20050 | 0.009420 | 1225.470638 |

Claim boundary: this ranks compilation/calibration diagnostics only. A selected layout still needs a gated hardware submission and baseline comparison.
