# Offline Nighthawk-calibrated Aer feasibility test

Scope before sampling: the existing 3x3 spinful Hubbard circuit (18 active
qubits), U/t=8, T=0.4, two Trotter steps, twirl 0, eight noisy trajectories.
No hardware submission, credential use, mitigation tuning or production sweep.

Use the archived provider-input QPY and original measurement/readout-X mapping.
Map physical wires and their full saved calibration together to local 0..17.
Do not transpile away native gates or simulate 120 dense qubits. The full
calibration is from earlier on 2026-09-05, not the exact last-job calibration.

Model: official Aer backend-model gate/readout helpers (Aer 0.17.2), native
gate depolarization plus T1/T2 gate-time relaxation and per-wire asymmetric
readout. Aer adjusts the depolarizing contribution for relaxation; do not add
the full reported gate infidelity again. Zero-temperature approximation.
Do not inject the reported init_error or add guessed idle scheduling. Later
idle-gap, coherent, correlated and drift models would be sensitivity studies.

Compatibility finding before sampling: the saved properties omit frequency.
`NoiseModel.from_backend_properties` fails in its automatic delay-pass wrapper
with Runtime 0.48.0's BackendPropertyError. Use its public
`basic_device_gate_errors` and `basic_device_readout_errors` building blocks
directly. At temperature=0, excited-state population is zero regardless of
frequency. No frequency is fabricated, no T1/T2 or gate noise is disabled.
This circuit has no delays; the unused automatic delay pass is not installed.

Units: retain archived us/ns labels; BackendProperties converts times to SI
seconds and Aer handles its internal conversions. Model evolution time T is
dimensionless (hopping*t/hbar), distinct from device gate duration in seconds.
Wire map q_local=j <-> physical=layout[j]; printed bitstrings are MSB-first,
decoded bits are little-endian and XOR the saved readout mask. Z=1-2*n;
spin=n_up-n_down, charge=n_up+n_down, doublon=n_up*n_down.

Checks before noise sampling:

- All native instructions, counts and measurement bits preserved.
- Every CZ is allowed by the cached device coupling map.
- Every X/SX/CZ and measured qubit has its mapped calibration noise channel.
- Full noise-free Pauli vector agrees with the frozen exact finite-circuit
  reference to 1e-9; norm is 1 and probability outside Nup=Ndown=4 is <1e-9.
- Unit tests check asymmetric physical noise remapping and mirrored CZ support.

Expected outcome: the circuit runs and returns exactly eight 18-bit samples;
nonzero calibrated noise channels are present. No particular physical means
or retention are predicted from eight shots. Worst-case standard error of a
single Pauli sample mean is 1/sqrt(8) ~0.35; no accuracy claim is supported.
Statevector storage is 2^18*16=4 MiB per trajectory (excluding overhead),
whereas a dense 18-qubit density matrix would be 1 TiB and is not used.

Save source/input hashes, calibration, noise model, circuit, raw samples,
versions and runtime. Preserve all hardware archives. Next, if feasible,
compare a matched 512-shot Aer pilot against existing RAW hardware observations
before evaluating diverse U0 calibration patterns and mitigation. Synthetic
training and testing alone would not establish transfer to real hardware.

References: https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.noise.NoiseModel.html
and https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.AerSimulator.html
