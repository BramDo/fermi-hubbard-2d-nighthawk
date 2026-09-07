# 2D Cuprate Hubbard Gaussian/Majorana Baseline

This is an exact free-fermion baseline for the U=0 part of the same t-t' model.

- lattice/qubits: 3x3 / 18
- holes/doping: 1/0.111111
- simulated interaction: U/t = 0 baseline; target U/t = 8
- t'/t: -0.25
- steps/dt/time: 4/0.1/0.4

## Diagnostics

- elapsed seconds: 0.002468
- total charge initial/final: 8/8
- total spin-z initial/final: 6.66133814775e-16/-1.16573417586e-15
- max abs charge change: 0.508836
- max abs spin-z change: 0.594422
- mean final double occupancy product: 0.155495

## Artifacts

- observables CSV: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/time_sweep_steps4/gaussian_majorana_baseline/cuprate_2d_gaussian_observables.csv`
- summary JSON: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/time_sweep_steps4/gaussian_majorana_baseline/cuprate_2d_gaussian_summary.json`
- plot: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/time_sweep_steps4/gaussian_majorana_baseline/cuprate_2d_gaussian_charge_spin.png`

Claim boundary: this baseline ignores U and cannot replace the interacting 72q circuit or tensor-network benchmarks.
