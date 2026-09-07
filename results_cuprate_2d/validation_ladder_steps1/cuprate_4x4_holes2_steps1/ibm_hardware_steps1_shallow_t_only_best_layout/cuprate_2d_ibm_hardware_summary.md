# IBM 72q 2D Cuprate Hubbard Hardware Test

- backend: `ibm_marrakesh`
- job id: `d93v9a6vtlqs73ftm6mg`
- shots: 1024
- lattice/qubits: 4x4 / 32
- steps/dt: 1/0.1
- U/t: 8.0
- t'/t: -0.25

## Local Observables

| profile | total charge | total spin-z | mean |spin-z| | mean doublon | min charge | max charge |
|---|---:|---:|---:|---:|---:|---:|
| raw | 13.766602 | -0.340820 | 0.650818 | 0.072632 | 0.253906 | 1.037109 |
| readout_corrected | 13.881690 | -0.242608 | 0.685372 | 0.064137 | 0.259119 | 1.095646 |

## Particle Sector

- expected N_up/N_down: 7/7
- exact sector fraction: 0.129883
- mean abs N_up error: 0.873047
- mean abs N_down error: 0.932617

## Artifacts

- raw_results_json: `results_cuprate_2d/validation_ladder_steps1/cuprate_4x4_holes2_steps1/ibm_hardware_steps1_shallow_t_only_best_layout/cuprate_2d_ibm_raw_results.json`
- site_observables_csv: `results_cuprate_2d/validation_ladder_steps1/cuprate_4x4_holes2_steps1/ibm_hardware_steps1_shallow_t_only_best_layout/cuprate_2d_ibm_site_observables.csv`
- bond_observables_csv: `results_cuprate_2d/validation_ladder_steps1/cuprate_4x4_holes2_steps1/ibm_hardware_steps1_shallow_t_only_best_layout/cuprate_2d_ibm_bond_observables.csv`
- plot: `results_cuprate_2d/validation_ladder_steps1/cuprate_4x4_holes2_steps1/ibm_hardware_steps1_shallow_t_only_best_layout/cuprate_2d_ibm_readout_corrected_observables.png`

Claim boundary: this is a hardware smoke test of diagonal observables, not a superconductivity claim.
