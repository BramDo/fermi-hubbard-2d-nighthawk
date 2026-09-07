# 2D Cuprate Validation Case: cuprate_6x6_holes4_steps1

Local dry-run only. No IBM Runtime, Fire Opal, or hardware job was submitted.

## Target

- lattice/sites/qubits: 6x6 / 36 / 72
- holes/doping: 4/0.111111
- U/t, t'/t: 8, -0.25
- steps/dt/time: 1/0.1/0.1

## Circuit Resource

- logical depth/two-qubit depth/two-qubit count: 5081/4235/8232
- qelib depth/two-qubit depth/two-qubit count: 4761/4235/8232
- abstract QASM characters: 166933
- qelib QASM characters: 168805

## Local Baseline Check

- TDHF mean doublon: 0.023967
- Gaussian mean doublon: 0.025179
- Gaussian vs TDHF RMSE charge/spin/doublon: 0.000195/0.002836/0.001297

## Fire Opal Input

- abstract for Fire Opal: True
- qasm basis: native
- backend transpile: False
- warnings: `['none']`

## Artifacts

- config: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/cuprate_2d_config.json`
- initial preview: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/cuprate_2d_initial_state.png`
- TDHF observables: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/cuprate_2d_tdhf_observables.csv`
- Gaussian observables: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/cuprate_2d_gaussian_observables.csv`
- Fire Opal abstract plan: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/fire_opal_abstract_dryrun/fire_opal_plan.json`
- Fire Opal abstract manifest: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/fire_opal_abstract_dryrun/fire_opal_qasm_manifest.json`
- qelib reference manifest: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/fire_opal_qelib_reference_dryrun/fire_opal_qasm_manifest.json`

Claim boundary: this case is a validation step. Passing it does not validate the larger 6x6 hardware result.
