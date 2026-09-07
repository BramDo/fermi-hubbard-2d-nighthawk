# 2D Cuprate Hubbard TDHF Simulation

This is a fast classical mean-field simulation for the separate 2D cuprate target.
It is useful for charge/spin dynamics and pipeline checks, not for a superconductivity claim.

## Target

- lattice: 3x3
- sites/qubits in matching JW target: 9/18
- holes/doping: 1/0.111111
- U/t: 8
- t'/t: -0.25
- steps/dt/time: 4/0.1/0.4

## Diagnostics

- elapsed seconds: 0.095835
- internal steps: 80
- total charge initial/final: 8/8
- total spin-z initial/final: 0/-1.27675647832e-15
- max abs charge change: 0.401605
- max abs spin-z change: 0.369831
- mean final double occupancy, mean-field: 0.0945338

## Artifacts

- observables CSV: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/time_sweep_steps4/tdhf_simulation/cuprate_2d_tdhf_observables.csv`
- summary JSON: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/time_sweep_steps4/tdhf_simulation/cuprate_2d_tdhf_summary.json`
- plot: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/time_sweep_steps4/tdhf_simulation/cuprate_2d_tdhf_charge_spin.png`

Claim boundary: TDHF discards connected many-body correlations and cannot establish d-wave superconductivity.
