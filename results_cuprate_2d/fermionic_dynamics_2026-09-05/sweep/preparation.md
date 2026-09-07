# Full-fermion 2D dynamics preparation

Circuit family: fermionic_jw_symmetric. All t, t-prime and U terms included.
Only classical circuit construction and optional read-only backend transpilation were performed. No QPU job was submitted.

| steps | time | logical 2q | routed 2q | routed depth |
|---|---:|---:|---:|---:|
| 2 | 0.20 | 15512 | 67793 | 63098 |
| 4 | 0.40 | 31024 | 136653 | 132008 |
| 8 | 0.80 | 62048 | 275834 | 256615 |

Future ZNE setting: 512 shots per factor, factors 1/3/5, maximum execution time 5 s.
The old t-only MPS/hardware results are not references for these corrected circuits.
Before hardware physics: establish dt and MPS-bond convergence for the chosen time and assess the much deeper routed circuit.
Source validation and circuit/observable inputs are preserved beside every plan.
