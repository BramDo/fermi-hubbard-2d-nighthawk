# 2D Cuprate Validation Case: cuprate_4x4_holes2_steps1

Local dry-run only. No IBM Runtime, Fire Opal, or hardware job was submitted.

## Target

- lattice/sites/qubits: 4x4 / 16 / 32
- holes/doping: 2/0.125000
- U/t, t'/t: 8, -0.25
- steps/dt/time: 1/0.1/0.1

## Circuit Resource

- logical depth/two-qubit depth/two-qubit count: 1694/1331/2144
- qelib depth/two-qubit depth/two-qubit count: 1557/1331/2144
- abstract QASM characters: 47395
- qelib QASM characters: 48286

## Local Baseline Check

- TDHF mean doublon: 0.019260
- Gaussian mean doublon: 0.020219
- Gaussian vs TDHF RMSE charge/spin/doublon: 0.000300/0.002310/0.001043

## Fire Opal Input

- abstract for Fire Opal: True
- qasm basis: native
- backend transpile: False
- warnings: `['none']`

## Artifacts

- config: `results_cuprate_2d/validation_ladder_steps1/cuprate_4x4_holes2_steps1/cuprate_2d_config.json`
- initial preview: `results_cuprate_2d/validation_ladder_steps1/cuprate_4x4_holes2_steps1/cuprate_2d_initial_state.png`
- TDHF observables: `results_cuprate_2d/validation_ladder_steps1/cuprate_4x4_holes2_steps1/cuprate_2d_tdhf_observables.csv`
- Gaussian observables: `results_cuprate_2d/validation_ladder_steps1/cuprate_4x4_holes2_steps1/cuprate_2d_gaussian_observables.csv`
- Fire Opal abstract plan: `results_cuprate_2d/validation_ladder_steps1/cuprate_4x4_holes2_steps1/fire_opal_abstract_dryrun/fire_opal_plan.json`
- Fire Opal abstract manifest: `results_cuprate_2d/validation_ladder_steps1/cuprate_4x4_holes2_steps1/fire_opal_abstract_dryrun/fire_opal_qasm_manifest.json`
- qelib reference manifest: `results_cuprate_2d/validation_ladder_steps1/cuprate_4x4_holes2_steps1/fire_opal_qelib_reference_dryrun/fire_opal_qasm_manifest.json`

Claim boundary: this case is a validation rung. Passing it does not validate the larger 6x6 hardware result.
