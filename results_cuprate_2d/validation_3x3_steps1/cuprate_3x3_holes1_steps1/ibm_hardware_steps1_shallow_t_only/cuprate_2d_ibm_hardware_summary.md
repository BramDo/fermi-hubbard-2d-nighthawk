# IBM 72q 2D Cuprate Hubbard Hardware Test

- backend: `ibm_marrakesh`
- job id: `d93r4otgc6cc73fe9f0g`
- shots: 1024
- lattice/qubits: 3x3 / 18
- steps/dt: 1/0.1
- U/t: 8.0
- t'/t: -0.25

## Local Observables

| profile | total charge | total spin-z | mean |spin-z| | mean doublon | min charge | max charge |
|---|---:|---:|---:|---:|---:|---:|
| raw | 7.536133 | 0.493164 | 0.655273 | 0.063260 | 0.222656 | 1.067383 |
| readout_corrected | 7.564247 | 0.518122 | 0.673231 | 0.057248 | 0.226334 | 1.076587 |

## Particle Sector

- expected N_up/N_down: 4/4
- exact sector fraction: 0.224609
- mean abs N_up error: 0.469727
- mean abs N_down error: 0.800781

## Artifacts

- raw_results_json: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/ibm_hardware_steps1_shallow_t_only/cuprate_2d_ibm_raw_results.json`
- site_observables_csv: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/ibm_hardware_steps1_shallow_t_only/cuprate_2d_ibm_site_observables.csv`
- bond_observables_csv: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/ibm_hardware_steps1_shallow_t_only/cuprate_2d_ibm_bond_observables.csv`
- plot: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/ibm_hardware_steps1_shallow_t_only/cuprate_2d_ibm_readout_corrected_observables.png`

Claim boundary: this is a hardware smoke test of diagonal observables, not a superconductivity claim.
