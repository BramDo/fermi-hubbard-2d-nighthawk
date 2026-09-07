# 2D Cuprate Hubbard TDHF Simulation

This is a fast classical mean-field simulation for the separate 2D cuprate target.
It is useful for charge/spin dynamics and pipeline checks, not for a superconductivity claim.

## Target

- lattice: 6x6
- sites/qubits in matching JW target: 36/72
- holes/doping: 4/0.111111
- U/t: 8
- t'/t: -0.25
- steps/dt/time: 1/0.1/0.1

## Diagnostics

- elapsed seconds: 0.236034
- internal steps: 20
- total charge initial/final: 32/32
- total spin-z initial/final: 0/-1.11369247158e-15
- max abs charge change: 0.0211132
- max abs spin-z change: 0.0745051
- mean final double occupancy, mean-field: 0.0239668

## Artifacts

- observables CSV: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/tdhf_simulation_steps1/cuprate_2d_tdhf_observables.csv`
- summary JSON: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/tdhf_simulation_steps1/cuprate_2d_tdhf_summary.json`
- plot: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/tdhf_simulation_steps1/cuprate_2d_tdhf_charge_spin.png`

Claim boundary: TDHF discards connected many-body correlations and cannot establish d-wave superconductivity.
