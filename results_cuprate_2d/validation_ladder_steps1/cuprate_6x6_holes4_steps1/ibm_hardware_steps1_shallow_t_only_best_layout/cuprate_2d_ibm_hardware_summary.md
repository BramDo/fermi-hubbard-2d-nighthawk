# IBM 72q 2D Cuprate Hubbard Hardware Test

- backend: `ibm_marrakesh`
- job id: `d94cogcql68s73c9clg0`
- shots: 1024
- lattice/qubits: 6x6 / 72
- steps/dt: 1/0.1
- U/t: 8.0
- t'/t: -0.25

## Local Observables

| profile | total charge | total spin-z | mean |spin-z| | mean doublon | min charge | max charge |
|---|---:|---:|---:|---:|---:|---:|
| raw | 31.205078 | -0.591797 | 0.226237 | 0.171224 | 0.457031 | 1.335938 |
| readout_corrected | 31.153041 | -0.455994 | 0.237755 | 0.168657 | 0.417798 | 1.345058 |

## Particle Sector

- expected N_up/N_down: 16/16
- exact sector fraction: 0.018555
- mean abs N_up error: 2.238281
- mean abs N_down error: 2.238281

## Artifacts

- raw_results_json: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/ibm_hardware_steps1_shallow_t_only_best_layout/cuprate_2d_ibm_raw_results.json`
- site_observables_csv: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/ibm_hardware_steps1_shallow_t_only_best_layout/cuprate_2d_ibm_site_observables.csv`
- bond_observables_csv: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/ibm_hardware_steps1_shallow_t_only_best_layout/cuprate_2d_ibm_bond_observables.csv`
- plot: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/ibm_hardware_steps1_shallow_t_only_best_layout/cuprate_2d_ibm_readout_corrected_observables.png`

Claim boundary: this is a hardware smoke test of diagonal observables, not a superconductivity claim.
