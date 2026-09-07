# IBM 72q 2D Cuprate Hubbard Hardware Test

- backend: `ibm_marrakesh`
- job id: `d93sqjdgc6cc73feca6g`
- shots: 1024
- lattice/qubits: 3x3 / 18
- steps/dt: 2/0.1
- U/t: 8.0
- t'/t: -0.25

## Local Observables

| profile | total charge | total spin-z | mean |spin-z| | mean doublon | min charge | max charge |
|---|---:|---:|---:|---:|---:|---:|
| raw | 7.208984 | 0.234375 | 0.491536 | 0.090169 | 0.429688 | 0.981445 |
| readout_corrected | 7.247444 | 0.222842 | 0.502563 | 0.088789 | 0.434654 | 0.985728 |

## Particle Sector

- expected N_up/N_down: 4/4
- exact sector fraction: 0.137695
- mean abs N_up error: 0.827148
- mean abs N_down error: 0.856445

## Artifacts

- raw_results_json: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/ibm_hardware_steps2_shallow_t_only/cuprate_2d_ibm_raw_results.json`
- site_observables_csv: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/ibm_hardware_steps2_shallow_t_only/cuprate_2d_ibm_site_observables.csv`
- bond_observables_csv: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/ibm_hardware_steps2_shallow_t_only/cuprate_2d_ibm_bond_observables.csv`
- plot: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/ibm_hardware_steps2_shallow_t_only/cuprate_2d_ibm_readout_corrected_observables.png`

Claim boundary: this is a hardware smoke test of diagonal observables, not a superconductivity claim.
