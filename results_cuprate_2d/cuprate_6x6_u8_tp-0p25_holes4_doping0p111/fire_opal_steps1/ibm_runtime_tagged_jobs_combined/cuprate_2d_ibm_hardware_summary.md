# IBM 72q 2D Cuprate Hubbard Hardware Test

- backend: `ibm_marrakesh`
- job id: `fireopal_ibm_jobs_main_d93ap6l958jc73bspr10_readout_d93ak58oamcc73dc0lo0`
- shots: 512
- lattice/qubits: 6x6 / 72
- steps/dt: 4/0.1
- U/t: 8.0
- t'/t: -0.25

## Local Observables

| profile | total charge | total spin-z | mean |spin-z| | mean doublon | min charge | max charge |
|---|---:|---:|---:|---:|---:|---:|
| raw | 35.617188 | -0.750000 | 0.045356 | 0.245877 | 0.644531 | 1.265625 |
| readout_corrected | 35.970648 | -0.407636 | 0.053781 | 0.251017 | 0.645754 | 1.318170 |

## Particle Sector

- expected N_up/N_down: 16/16
- exact sector fraction: 0.015625
- mean abs N_up error: 2.613281
- mean abs N_down error: 2.886719

## Artifacts

- raw_results_json: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/fire_opal_steps1/ibm_runtime_tagged_jobs_combined/cuprate_2d_ibm_raw_results.json`
- site_observables_csv: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/fire_opal_steps1/ibm_runtime_tagged_jobs_combined/cuprate_2d_ibm_site_observables.csv`
- bond_observables_csv: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/fire_opal_steps1/ibm_runtime_tagged_jobs_combined/cuprate_2d_ibm_bond_observables.csv`
- plot: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/fire_opal_steps1/ibm_runtime_tagged_jobs_combined/cuprate_2d_ibm_readout_corrected_observables.png`

Claim boundary: this is a hardware smoke test of diagonal observables, not a superconductivity claim.
