# 2D Cuprate Hubbard Pipeline

Separate pipeline from the existing 1D 60q/120q Fermi-Hubbard workflow.

## Target

- lattice: 6x6 square lattice
- sites/qubits: 36/72
- holes/doping: 4/0.111111
- U/t: 8
- t'/t: -0.25
- boundary: x=open, y=open
- Trotter sketch: steps=4, dt=0.1, total_time=0.4

## Generated Artifacts

- config: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/cuprate_2d_config.json`
- mode order: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/cuprate_2d_mode_order.json`
- initial state CSV: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/cuprate_2d_initial_state.csv`
- bond list: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/cuprate_2d_bonds.csv`
- resource estimate JSON: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/cuprate_2d_resource_estimate.json`
- hopping terms CSV: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/cuprate_2d_hopping_terms.csv`
- observable plan JSON: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/cuprate_2d_observable_plan.json`
- observable plan CSV: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/cuprate_2d_observable_plan.csv`
- reference targets JSON: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/cuprate_2d_reference_targets.json`
- reference targets report: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/cuprate_2d_reference_targets.md`
- initial state preview: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/cuprate_2d_initial_state.png`

## Observable Boundary

- Z-basis output can support charge density, spin-z density, doublons, and diagonal spin/charge correlations.
- d-wave superconductivity needs off-diagonal pair correlators such as `<Delta_d^dagger(i) Delta_d(j)>`.
- Stripe evidence should be reported through charge/spin structure factors and real-space modulation, not by visual inspection only.

## Rough Explicit-JW Resources

- nearest-neighbor bonds: 60
- next-nearest-neighbor t' bonds: 50
- hopping Pauli rotations per step: 440
- onsite ZZ rotations per step: 36
- max JW string weight: 15
- rough CNOT ladder count per step: 8232
- rough CNOT ladder count total: 32928

Claim boundary: this resource estimate is intentionally conservative and not hardware-routed. A real 2D hardware path needs a separate fermionic routing/fSWAP compilation step.
