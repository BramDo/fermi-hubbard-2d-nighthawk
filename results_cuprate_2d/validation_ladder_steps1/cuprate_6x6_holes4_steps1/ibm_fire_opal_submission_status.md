# 6x6 IBM and Fire Opal Submission Status

Submitted on 2026-07-04 after explicit user request.

## IBM Runtime

- route: `ibm_hardware_steps1_shallow_t_only_best_layout`
- backend: `ibm_marrakesh`
- job id: `d94cogcql68s73c9clg0`
- submitted at UTC: `2026-07-04T09:02:59.498339+00:00`
- latest checked status: `DONE`
- shots: 1024
- readout repetitions: 3
- requested readout shots: 4096
- best layout seed: 26
- transpiled main two-qubit count/depth/depth: 2397 / 317 / 759

## IBM Result Snapshot

| profile | total charge | total spin-z | mean abs spin-z | mean doublon |
|---|---:|---:|---:|---:|
| IBM raw | 31.205078 | -0.591797 | 0.226237 | 0.171224 |
| IBM readout corrected | 31.153041 | -0.455994 | 0.237755 | 0.168657 |
| MPS chi32 reference | 32.000000 | 0.000000 | 0.840386 | 0.023625 |

RMSE versus MPS chi32:

| profile | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---:|---:|---:|
| IBM raw | 0.332687 | 0.733615 | 0.167283 |
| IBM readout corrected | 0.330085 | 0.731364 | 0.166579 |

Particle-sector diagnostic:

- expected N_up/N_down: 16 / 16
- exact sector fraction: 0.018555
- mean abs N_up error: 2.238281
- mean abs N_down error: 2.238281

## Fire Opal

- route: `fire_opal_shallow_t_only_abstract`
- backend: `ibm_marrakesh`
- main action id: `2331687`
- readout action id: `2331688`
- main status: `FAILURE`
- readout status at latest poll: `PENDING`
- main created/updated UTC-like timestamps from Fire Opal metadata: `2026-07-04 09:04:31` / `2026-07-04 09:04:39`
- failure reason from `fireopal.get_result(2331687)`: Fire Opal rejected the main QASM because `rzz` is a reserved gate name from `qelib1.inc`; the submitted abstract/native QASM also contains custom `xx_plus_yy` gates.

No usable Fire Opal observables are available from this abstract submission because the main action failed.

## Comparison Artifacts

- IBM summary: `ibm_hardware_steps1_shallow_t_only_best_layout/cuprate_2d_ibm_hardware_summary.md`
- IBM site observables: `ibm_hardware_steps1_shallow_t_only_best_layout/cuprate_2d_ibm_site_observables.csv`
- Fire Opal status: `fire_opal_shallow_t_only_abstract/fire_opal_action_status.json`
- normalized comparison: `observable_comparison_shallow_t_only_steps1_vs_mps_hardware/cuprate_2d_observable_comparison.md`

Claim boundary: this is hardware diagnostic output for diagonal observables. It is not a superconductivity or material-physics claim until it survives sector/observable validation against local baselines.
