# IBM 72q 2D Cuprate Hubbard Hardware Test

- backend: `ibm_phoenix`
- job id: `dadgm5dnj4cs73ads6ng`
- shots: 128
- lattice/qubits: 6x6 / 72
- steps/dt: 1/0.1
- U/t: 8.0
- t'/t: -0.25

## Local Observables

| profile | total charge | total spin-z | mean |spin-z| | mean doublon | min charge | max charge |
|---|---:|---:|---:|---:|---:|---:|
| raw | 31.140625 | -0.234375 | 0.650608 | 0.072700 | 0.226562 | 1.046875 |
| readout_corrected | 31.808619 | -0.364044 | 0.672312 | 0.072753 | 0.232207 | 1.099239 |

## Particle Sector

- expected N_up/N_down: 16/16
- exact sector fraction: 0.054688
- mean abs N_up error: 1.406250
- mean abs N_down error: 1.390625

## Artifacts

- raw_results_json: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/ibm_phoenix_budgeted_s128_max5s/cuprate_2d_ibm_raw_results.json`
- site_observables_csv: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/ibm_phoenix_budgeted_s128_max5s/cuprate_2d_ibm_site_observables.csv`
- bond_observables_csv: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/ibm_phoenix_budgeted_s128_max5s/cuprate_2d_ibm_bond_observables.csv`
- plot: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/ibm_phoenix_budgeted_s128_max5s/cuprate_2d_ibm_readout_corrected_observables.png`

Claim boundary: this is a hardware smoke test of diagonal observables, not a superconductivity claim.
