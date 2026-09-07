# 2D Cuprate Validation Ladder

Local planning and baseline validation only. No IBM Runtime, Fire Opal, or hardware job was submitted.

The ladder reduces circuit depth before another hardware run and prepares abstract Fire Opal dry-run inputs.

## Ladder Summary

| case | qubits | holes | doping | logical 2q count | logical 2q depth | qelib 2q count | qelib 2q depth | qelib 2q count vs 6x6 | Gaussian charge RMSE | Gaussian spin RMSE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cuprate_2x3_holes1_steps1 | 12 | 1 | 0.166667 | 316 | 241 | 316 | 241 | 0.038 | 0.000252 | 0.001541 |
| cuprate_3x3_holes1_steps1 | 18 | 1 | 0.111111 | 786 | 589 | 786 | 589 | 0.095 | 0.000373 | 0.001896 |
| cuprate_4x4_holes2_steps1 | 32 | 2 | 0.125000 | 2144 | 1331 | 2144 | 1331 | 0.260 | 0.000300 | 0.002310 |
| cuprate_6x6_holes4_steps1 | 72 | 4 | 0.111111 | 8232 | 4235 | 8232 | 4235 | 1.000 | 0.000195 | 0.002836 |

## Recommended Hardware Gate

1. Use the smallest case that exercises both x/y hopping and t' diagonals before retrying 6x6.
2. Prefer the `fire_opal_abstract_dryrun` plans, which use native, non-backend-transpiled QASM.
3. Require sector survival and same-observable RMSE to pass on a small rung before scaling up.

Interpretation boundary: these are resource and baseline checks, not hardware evidence.
