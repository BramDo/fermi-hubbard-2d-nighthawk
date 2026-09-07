# IBM 72q 2D Cuprate Hubbard Hardware Test

- backend: `ibm_marrakesh`
- job id: `d93aa8l958jc73bspbvg`
- shots: 512
- lattice/qubits: 6x6 / 72
- steps/dt: 1/0.1
- U/t: 8.0
- t'/t: -0.25

## Local Observables

| profile | total charge | total spin-z | mean |spin-z| | mean doublon | min charge | max charge |
|---|---:|---:|---:|---:|---:|---:|
| raw | 12.503906 | 0.378906 | 0.103407 | 0.049154 | 0.005859 | 0.943359 |
| readout_corrected | 11.897078 | 0.650545 | 0.108421 | 0.045790 | 0.005894 | 0.946898 |

## Particle Sector

- expected N_up/N_down: 16/16
- exact sector fraction: 0.000000
- mean abs N_up error: 9.558594
- mean abs N_down error: 9.937500

## Artifacts

- raw_results_json: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/ibm_hardware_steps1/cuprate_2d_ibm_raw_results.json`
- site_observables_csv: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/ibm_hardware_steps1/cuprate_2d_ibm_site_observables.csv`
- bond_observables_csv: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/ibm_hardware_steps1/cuprate_2d_ibm_bond_observables.csv`
- plot: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/ibm_hardware_steps1/cuprate_2d_ibm_readout_corrected_observables.png`

Claim boundary: this is a hardware smoke test of diagonal observables, not a superconductivity claim.
