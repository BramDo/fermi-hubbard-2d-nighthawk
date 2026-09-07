# 6x6 IBM and Fire Opal Preparation

Prepared on 2026-07-04 for the validation-ladder 6x6, 4-hole, steps=1 shallow circuit case.

No IBM Runtime, Fire Opal, or hardware job was submitted in this preparation step.

## Target

- lattice/sites/qubits: 6x6 / 36 / 72
- holes/doping: 4 / 0.111111
- U/t, t'/t: 8, -0.25
- steps/dt/time: 1 / 0.1 / 0.1
- circuit family: `number_preserving_t_only`
- backend selected for preparation: `ibm_marrakesh`

## Current Backend Read

- `ibm_marrakesh`: 156 qubits, pending=2, operational=True at the queue precheck
- layout scout plan snapshot: pending=7, operational=True

## IBM Preparation

- layout scout: `layout_scout_shallow_t_only`
- best candidate: `sabre_seed_26`
- best seed: `26`
- layout scout two-qubit count/depth/depth: 1164 / 138 / 367
- IBM dry-run plan: `ibm_hardware_steps1_shallow_t_only_best_layout_plan`
- IBM plan submit flag: `False`
- IBM planned shots: 1024
- IBM requested readout repetitions/shots: 3 / 4096
- IBM dry-run transpiled main two-qubit count/depth/depth: 2397 / 317 / 759

Run only when an explicit submit decision is made:

- `scripts/submit_cuprate_2d_6x6_ibm_shallow_t_only_best_layout_wsl.ps1`

Retrieve after a submitted job exists:

- `scripts/retrieve_cuprate_2d_6x6_ibm_shallow_t_only_best_layout_wsl.ps1`

## Fire Opal Preparation

- dry-run output: `fire_opal_shallow_t_only_abstract_dryrun`
- Fire Opal plan submit flag: `False`
- abstract input: `True`
- qasm basis: `native`
- backend transpile before Fire Opal: `False`
- main/readout shots: 1024 / 4096
- main logical/native two-qubit count/depth/depth: 156 / 5 / 8
- main QASM characters: 10473

Run only when an explicit submit decision is made:

- `scripts/submit_cuprate_2d_6x6_fire_opal_shallow_t_only_abstract_wsl.ps1`

Retrieve after submitted Fire Opal actions exist:

- `scripts/retrieve_cuprate_2d_6x6_fire_opal_shallow_t_only_abstract_wsl.ps1`

## Baseline Comparison Anchor

The post-result comparison wrapper is ready:

- `scripts/compare_cuprate_2d_6x6_shallow_t_only_vs_mps_wsl.ps1`
- output: `observable_comparison_shallow_t_only_steps1_vs_mps_hardware`
- reference source: `mps32:mps_chi32`

Current local-only RMSE versus MPS chi32:

| source | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---:|---:|---:|
| TDHF mean-field | 0.001003 | 0.001905 | 0.000682 |
| Gaussian U=0 | 0.001181 | 0.004429 | 0.001750 |
| MPS chi16 | 0.001034 | 0.005384 | 0.002231 |

Claim boundary: this preparation validates only the execution artifacts and local diagonal-observable comparison path. Hardware output remains diagnostic until retrieved and compared against the local MPS/TDHF/Gaussian baselines.
