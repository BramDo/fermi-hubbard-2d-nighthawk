# 3x3 Exact Fixed-Sector 2D Cuprate Baseline

This is an exact diagonal-observable baseline in the fixed particle-number sector.

- model: `t_only_hubbard`
- lattice/qubits: 3x3 / 18
- sector N_up/N_down: 4/4
- basis dimension: 15876
- Hamiltonian nnz: 226926
- steps/dt/time: 4/0.1/0.4

## Final Diagonal Observables

- total charge: 8.000000
- total spin-z: -0.000000
- mean |spin-z|: 0.678740
- mean doublon: 0.061556

## Artifacts

- site observables: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/time_sweep_steps4/exact_sector_t_only_hubbard/cuprate_2d_exact_site_observables.csv`
- bond observables: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/time_sweep_steps4/exact_sector_t_only_hubbard/cuprate_2d_exact_bond_observables.csv`
- summary JSON: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/time_sweep_steps4/exact_sector_t_only_hubbard/cuprate_2d_exact_summary.json`

Claim boundary: this validates diagonal short-time many-body observables on the small 3x3 rung. It is not a tensor-network extrapolation and it does not measure off-diagonal d-wave pairing.
