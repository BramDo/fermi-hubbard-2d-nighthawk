# 2D Cuprate Hubbard Qiskit Circuit

This is a real Qiskit circuit for the separate 2D cuprate Hubbard target.
It uses explicit row-major Jordan-Wigner strings and first-order Trotterization.

## Target

- lattice: 6x6
- sites/qubits: 36/72
- holes/doping: 4/0.111111
- U/t: 8.0
- t'/t: -0.25
- steps/dt/time: 4/0.1/0.4

## Circuit

- qiskit circuit family: `cuprate-2d-explicit-row-major-jw`
- measured: True
- Hamiltonian Pauli terms per step: 548
- circuit depth: 12812
- two-qubit depth: 10610
- operation counts: `{'cx': 32928, 'h': 7040, 'rz': 2192, 'sdg': 1760, 's': 1760, 'measure': 72, 'x': 32, 'barrier': 1}`

## Artifacts

- QPY: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/qiskit_circuit/cuprate_2d_explicit_jw_trotter.qpy`
- OpenQASM 2: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/qiskit_circuit/cuprate_2d_explicit_jw_trotter.qasm`
- terms CSV: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/qiskit_circuit/cuprate_2d_explicit_jw_terms.csv`
- summary JSON: `results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111/qiskit_circuit/cuprate_2d_qiskit_circuit_summary.json`

Claim boundary: this is not yet hardware-routed. A hardware run still needs layout/routing, backend inspection, and a submit gate.
