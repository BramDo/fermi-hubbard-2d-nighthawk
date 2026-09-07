# IBM 72q 2D Cuprate Hubbard Hardware Test

- backend: `ibm_phoenix`
- job id: `dadhca3dd5gc73d7b8vg`
- shots: 128
- lattice/qubits: 6x6 / 72
- steps/dt: 1/0.1
- U/t: 8.0
- t'/t: -0.25

## Local Observables

| profile | total charge | total spin-z | mean |spin-z| | mean doublon | min charge | max charge |
|---|---:|---:|---:|---:|---:|---:|
| raw | 33.414062 | -0.554688 | 0.562717 | 0.128255 | 0.546875 | 1.250000 |
| readout_corrected | 34.018315 | -0.566423 | 0.576299 | 0.131602 | 0.558032 | 1.258063 |

## Particle Sector

- expected N_up/N_down: 16/16
- exact sector fraction: 0.007812
- mean abs N_up error: 1.804688
- mean abs N_down error: 2.265625

## Artifacts

- raw_results_json: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/ibm_phoenix_floquet_xy4_twirling_s128_max5s/cuprate_2d_ibm_raw_results.json`
- site_observables_csv: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/ibm_phoenix_floquet_xy4_twirling_s128_max5s/cuprate_2d_ibm_site_observables.csv`
- bond_observables_csv: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/ibm_phoenix_floquet_xy4_twirling_s128_max5s/cuprate_2d_ibm_bond_observables.csv`
- plot: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/ibm_phoenix_floquet_xy4_twirling_s128_max5s/cuprate_2d_ibm_readout_corrected_observables.png`

Claim boundary: this is a hardware smoke test of diagonal observables, not a superconductivity claim.
