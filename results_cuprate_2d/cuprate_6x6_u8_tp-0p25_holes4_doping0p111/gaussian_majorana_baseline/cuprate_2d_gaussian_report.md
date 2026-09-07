# 2D Cuprate Hubbard Gaussian/Majorana Baseline

This is an exact free-fermion baseline for the U=0 part of the same t-t' model.

- lattice/qubits: 6x6 / 72
- holes/doping: 4/0.111111
- simulated interaction: U/t = 0 baseline; target U/t = 8
- t'/t: -0.25
- steps/dt/time: 1/0.1/0.1

## Diagnostics

- elapsed seconds: 0.059624
- total charge initial/final: 32/32
- total spin-z initial/final: -2.44249065418e-15/-2.44942954808e-15
- max abs charge change: 0.0216128
- max abs spin-z change: 0.0784346
- mean final double occupancy product: 0.0251785

## Artifacts

- observables CSV: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/gaussian_majorana_baseline/cuprate_2d_gaussian_observables.csv`
- summary JSON: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/gaussian_majorana_baseline/cuprate_2d_gaussian_summary.json`
- plot: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/gaussian_majorana_baseline/cuprate_2d_gaussian_charge_spin.png`

Claim boundary: this baseline ignores U and cannot replace the interacting 72q circuit or tensor-network benchmarks.
