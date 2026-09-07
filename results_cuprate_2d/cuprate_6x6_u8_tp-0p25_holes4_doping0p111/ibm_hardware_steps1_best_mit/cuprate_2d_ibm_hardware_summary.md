# IBM 72q 2D Cuprate Hubbard Hardware Test

- backend: `ibm_marrakesh`
- job id: `d93o3gkql68s73c8ij5g`
- shots: 1024
- lattice/qubits: 6x6 / 72
- steps/dt: 1/0.1
- U/t: 8.0
- t'/t: -0.25

## Local Observables

| profile | total charge | total spin-z | mean |spin-z| | mean doublon | min charge | max charge |
|---|---:|---:|---:|---:|---:|---:|
| raw | 17.526367 | -0.547852 | 0.104791 | 0.084581 | 0.007812 | 1.027344 |
| readout_corrected | 16.953522 | -0.497634 | 0.112525 | 0.082851 | 0.001655 | 1.043786 |

## Particle Sector

- expected N_up/N_down: 16/16
- exact sector fraction: 0.000000
- mean abs N_up error: 7.510742
- mean abs N_down error: 6.962891

## Artifacts

- raw_results_json: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/ibm_hardware_steps1_best_mit/cuprate_2d_ibm_raw_results.json`
- site_observables_csv: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/ibm_hardware_steps1_best_mit/cuprate_2d_ibm_site_observables.csv`
- bond_observables_csv: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/ibm_hardware_steps1_best_mit/cuprate_2d_ibm_bond_observables.csv`
- plot: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/ibm_hardware_steps1_best_mit/cuprate_2d_ibm_readout_corrected_observables.png`

Claim boundary: this is a hardware smoke test of diagonal observables, not a superconductivity claim.
