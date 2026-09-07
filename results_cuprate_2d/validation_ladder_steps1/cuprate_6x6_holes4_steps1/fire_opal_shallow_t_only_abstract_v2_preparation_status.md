# 6x6 Fire Opal shallow abstract v2 preparation

Status: dry-run prepared only. No IBM Runtime, Fire Opal, or hardware job was submitted in this step.

## Reason

The first shallow abstract Fire Opal submission failed on the Fire Opal side while using a native QASM input that contained a custom gate named `rzz`. Qiskit parsed that QASM locally, but the gate name is unsafe for Fire Opal because it can collide with reserved/imported gate names.

The qelib fallback avoided the name conflict, but it decomposed the circuit before Fire Opal and therefore reduced Fire Opal's freedom to optimize the input.

## Fix

The native QASM exporter now aliases Qiskit's `rzz` QASM call to `fo_rzz` when `--abstract-input` is used:

- old abstract QASM: `gate rzz(theta) ...` and `rzz(...)`
- v2 abstract QASM: `gate fo_rzz(theta) ...` and `fo_rzz(...)`

The physical definition remains the same:

`fo_rzz(theta) a,b { cx a,b; rz(theta) b; cx a,b; }`

## Dry-run evidence

Dry-run wrapper:

`scripts/run_cuprate_2d_6x6_fire_opal_shallow_t_only_abstract_v2_dryrun_wsl.ps1`

Prepared output:

`results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/fire_opal_shallow_t_only_abstract_v2_dryrun`

Main circuit parse summary:

| route | qasm basis | abstract for Fire Opal | parse ok | parse depth | two-qubit count | two-qubit depth | reserved `rzz` | alias |
|---|---|---:|---:|---:|---:|---:|---:|---|
| old shallow abstract | native | true | true | 8 | 156 | 5 | true | none |
| shallow abstract v2 | native | true | true | 8 | 156 | 5 | false | `rzz -> fo_rzz` |
| qelib fallback Fez dry-run | qelib | false | true | 25 | 312 | 10 | false | none |

Key v2 QASM checks:

- `contains_reserved_rzz`: false
- `contains_native_rzz_alias`: true
- `contains_custom_xx_plus_yy`: true
- Qiskit parse check: true

## Submit candidate

If explicitly requested later, use:

`scripts/submit_cuprate_2d_6x6_fire_opal_shallow_t_only_abstract_v2_wsl.ps1`

That wrapper writes to a new output directory:

`results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/fire_opal_shallow_t_only_abstract_v2`

This avoids reusing the old failed `fire_opal_shallow_t_only_abstract` submission directory.

## Interpretation boundary

This preparation only fixes the input quality for a future Fire Opal attempt. It is not hardware evidence. Any later hardware output remains diagnostic until compared against the MPS/TDHF/local observable comparison files and sector-conditioned validation.
