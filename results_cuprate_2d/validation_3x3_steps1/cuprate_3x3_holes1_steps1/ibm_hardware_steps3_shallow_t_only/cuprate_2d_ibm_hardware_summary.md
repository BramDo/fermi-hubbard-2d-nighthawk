# IBM 72q 2D Cuprate Hubbard Hardware Test

- backend: `ibm_marrakesh`
- job id: `d93t5fvu62ks73959ubg`
- shots: 1024
- lattice/qubits: 3x3 / 18
- steps/dt: 3/0.1
- U/t: 8.0
- t'/t: -0.25

## Local Observables

| profile | total charge | total spin-z | mean |spin-z| | mean doublon | min charge | max charge |
|---|---:|---:|---:|---:|---:|---:|
| raw | 7.503906 | 0.302734 | 0.452908 | 0.107205 | 0.466797 | 0.999023 |
| readout_corrected | 7.516324 | 0.356244 | 0.459429 | 0.104728 | 0.464408 | 1.004651 |

## Particle Sector

- expected N_up/N_down: 4/4
- exact sector fraction: 0.146484
- mean abs N_up error: 0.819336
- mean abs N_down error: 0.877930

## Artifacts

- raw_results_json: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/ibm_hardware_steps3_shallow_t_only/cuprate_2d_ibm_raw_results.json`
- site_observables_csv: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/ibm_hardware_steps3_shallow_t_only/cuprate_2d_ibm_site_observables.csv`
- bond_observables_csv: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/ibm_hardware_steps3_shallow_t_only/cuprate_2d_ibm_bond_observables.csv`
- plot: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/ibm_hardware_steps3_shallow_t_only/cuprate_2d_ibm_readout_corrected_observables.png`

Claim boundary: this is a hardware smoke test of diagonal observables, not a superconductivity claim.
