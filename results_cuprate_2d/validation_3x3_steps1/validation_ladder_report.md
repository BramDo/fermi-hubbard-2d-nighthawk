# 2D Cuprate Validation Ladder

Local planning and baseline validation only. No IBM Runtime, Fire Opal, or hardware job was submitted.

The ladder reduces circuit depth before another hardware run and prepares abstract Fire Opal dry-run inputs.

## Ladder Summary

| case | qubits | holes | doping | logical 2q count | logical 2q depth | qelib 2q count | qelib 2q depth | qelib 2q count vs 6x6 | Gaussian charge RMSE | Gaussian spin RMSE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cuprate_3x3_holes1_steps1 | 18 | 1 | 0.111111 | 786 | 589 | 786 | 589 | 1.000 | 0.000373 | 0.001896 |

## Recommended Hardware Gate

1. Use the smallest case that exercises both x/y hopping and t' diagonals before retrying 6x6.
2. Prefer the `fire_opal_abstract_dryrun` plans, which use native, non-backend-transpiled QASM.
3. Require sector survival and same-observable RMSE to pass on a small rung before scaling up.

Interpretation boundary: these are resource and baseline checks, not hardware evidence.
