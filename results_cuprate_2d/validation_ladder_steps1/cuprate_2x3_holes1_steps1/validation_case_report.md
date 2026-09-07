# 2D Cuprate Validation Case: cuprate_2x3_holes1_steps1

Local dry-run only. No IBM Runtime, Fire Opal, or hardware job was submitted.

## Target

- lattice/sites/qubits: 2x3 / 6 / 12
- holes/doping: 1/0.166667
- U/t, t'/t: 8, -0.25
- steps/dt/time: 1/0.1/0.1

## Circuit Resource

- logical depth/two-qubit depth/two-qubit count: 357/241/316
- qelib depth/two-qubit depth/two-qubit count: 313/241/316
- abstract QASM characters: 8205
- qelib QASM characters: 8572

## Local Baseline Check

- TDHF mean doublon: 0.012240
- Gaussian mean doublon: 0.012846
- Gaussian vs TDHF RMSE charge/spin/doublon: 0.000252/0.001541/0.000686

## Fire Opal Input

- abstract for Fire Opal: True
- qasm basis: native
- backend transpile: False
- warnings: `['none']`

## Artifacts

- config: `results_cuprate_2d/validation_ladder_steps1/cuprate_2x3_holes1_steps1/cuprate_2d_config.json`
- initial preview: `results_cuprate_2d/validation_ladder_steps1/cuprate_2x3_holes1_steps1/cuprate_2d_initial_state.png`
- TDHF observables: `results_cuprate_2d/validation_ladder_steps1/cuprate_2x3_holes1_steps1/cuprate_2d_tdhf_observables.csv`
- Gaussian observables: `results_cuprate_2d/validation_ladder_steps1/cuprate_2x3_holes1_steps1/cuprate_2d_gaussian_observables.csv`
- Fire Opal abstract plan: `results_cuprate_2d/validation_ladder_steps1/cuprate_2x3_holes1_steps1/fire_opal_abstract_dryrun/fire_opal_plan.json`
- Fire Opal abstract manifest: `results_cuprate_2d/validation_ladder_steps1/cuprate_2x3_holes1_steps1/fire_opal_abstract_dryrun/fire_opal_qasm_manifest.json`
- qelib reference manifest: `results_cuprate_2d/validation_ladder_steps1/cuprate_2x3_holes1_steps1/fire_opal_qelib_reference_dryrun/fire_opal_qasm_manifest.json`

Claim boundary: this case is a validation rung. Passing it does not validate the larger 6x6 hardware result.
