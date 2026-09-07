# IBM 72q 2D Cuprate Hubbard Hardware Test

- backend: `ibm_marrakesh`
- job id: `d93p8btgc6cc73fe6dm0`
- shots: 1024
- lattice/qubits: 3x3 / 18
- steps/dt: 1/0.1
- U/t: 8.0
- t'/t: -0.25

## Local Observables

| profile | total charge | total spin-z | mean |spin-z| | mean doublon | min charge | max charge |
|---|---:|---:|---:|---:|---:|---:|
| raw | 7.234375 | 0.117188 | 0.076606 | 0.171332 | 0.333008 | 1.055664 |
| readout_corrected | 7.219384 | 0.176720 | 0.084416 | 0.170556 | 0.335807 | 1.060086 |

## Particle Sector

- expected N_up/N_down: 4/4
- exact sector fraction: 0.082031
- mean abs N_up error: 1.095703
- mean abs N_down error: 1.167969

## Artifacts

- raw_results_json: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/ibm_hardware_steps1_best_mit/cuprate_2d_ibm_raw_results.json`
- site_observables_csv: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/ibm_hardware_steps1_best_mit/cuprate_2d_ibm_site_observables.csv`
- bond_observables_csv: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/ibm_hardware_steps1_best_mit/cuprate_2d_ibm_bond_observables.csv`
- plot: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/ibm_hardware_steps1_best_mit/cuprate_2d_ibm_readout_corrected_observables.png`

Claim boundary: this is a hardware smoke test of diagonal observables, not a superconductivity claim.
