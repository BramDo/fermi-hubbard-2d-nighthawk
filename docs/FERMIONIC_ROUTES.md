# Hubbard Routes: Circuit Identity and Review Clarification

Reviewed 19 October 2026. Geometry, circuit family and processor are separate
attributes. Running a circuit on Nighthawk does not make its hopping fermionic.

## Which Project Is Which?

| Route | Circuit/model | Hardware/results | Canonical location |
|---|---|---|---|
| Original spinful 1D snapshot | 30-site chain, 60 spin orbitals; its own fSWAP/mapping and TDVP workflow | IBM Kingston, 8 steps at dt=0.2; not the 2D Nighthawk experiment | [1D repository](https://github.com/BramDo/fermi-hubbard-60q-tdvp), [series 1](https://edukaizen.nl/fermi-hubbard-quantum-simulation-project/) |
| Historical 2D shallow route | `number_preserving_t_only`: bare XY hopping without nonlocal JW parity strings; diagonal t-prime skipped | Earlier Marrakesh and Fez/Fire Opal diagnostics, including 6x6 at T=0.1 | [Public historical repository](https://github.com/BramDo/fermi-hubbard-2d-cuprate), [series 2](https://edukaizen.nl/fermi-hubbard-2d-cuprate-series/) |
| Full-fermion 2D Nighthawk route | Fermionic swap network with parity signs, nearest hopping t, diagonal t-prime=-0.25 and onsite U=8; 36 sites, 72 spin orbitals, N=32 | `ibm_phoenix`; September paired experiment and October sparse dynamics are different jobs | [Private Nighthawk repository](https://github.com/BramDo/fermi-hubbard-2d-nighthawk), [series 3](https://edukaizen.nl/2d-local-quantum-advantage-en/) |
| Separate 1D package tutorial | `examples/qiskit_fermions_1d_flow_sets.py`: spinless chain with nearest-neighbour density interaction, not spinful onsite U | Local tutorial checks; logical depths are not routed 2D hardware depths | Example in the local research workspace; not evidence for the 72-mode experiment |

This is a route/provenance audit, not a new independent physics audit of the
original 1D code. The 1D snapshot must not be presented as a 120-qubit paper
reproduction or as validation of the later 2D circuit.

## What the Review Correctly Identified

The public July repository and older Edukaizen series document the historical
`number_preserving_t_only` family, not the later full-fermion experiment.
Configuration fields `U=8` and `t-prime=-0.25` alone do not establish which
Hamiltonian terms actually affect a circuit's ideal output.

There is an important U nuance: the legacy builder does insert diagonal onsite
RZ/RZZ gates, then applies hopping. For the recorded **one-step** run, the
onsite layer acts first on a computational-basis state. It contributes only a
global phase, so the ideal final measurement probabilities are U-independent.
This statement is not a claim that those physical gates have no noise cost,
and it does not apply to all multi-step circuits. Diagonal hopping is explicitly
omitted; bare nonlocal XY gates also omit fermionic parity strings.

The later `fermionic_jw_symmetric`, `fermionic_fswap_network` and
`tflo_fixed_network` implementations retain the fermionic signs and full t-t'-U
terms. Their finite-step orderings and references must still be distinguished.
The TFLO target uses U=8; its training/holdout circuits intentionally use U=0.

## Latest 6x6 Measurements

The October 5 sparse series is the full-fermion network on `ibm_phoenix`, the
Nighthawk backend, not the earlier Fez/Marrakesh circuit. There are 72 logical
spin-orbitals; the processor has 120 physical qubits. Four independent jobs
each recorded 6 QPU seconds (24 total), including their controls.

| T | Job ID | MPS chi64 mean D | Diagnostic readout+TFLO mean D |
|---|---|---:|---:|
| 0.2 | db1tkjpmmimc73fnv1f0 | 0.064123113 | 0.118889753 |
| 0.4 | db1tujhmmimc73fnvdb0 | 0.087896063 | 0.110335297 |
| 0.6 | db1u8bhre0kc7396s6fg | 0.053481612 | 0.133942448 |
| 0.8 | db1uj5n2iglc7396jv60 | 0.061595521 | 0.147333202 |

At T=0.8, classical chi128 gives D=0.072687424 instead of chi64's 0.061595521.
The distance to the diagnostic hardware point falls by about 13%. This is not
an established reduction in physical error: MPS convergence has not been
demonstrated and the independent U=0/TFLO screens fail at all four times.
No new hardware was used for the chi128 refinement or this review.

Google's cited 6x6 comparison has N=30 and no diagonal hopping; ours has N=32
and t-prime=-0.25, with a different initial stripe. Similar observable scale
is meaningful context, but neither "Google-level accuracy" nor a universal
"twice Google's error" follows. Mean D differences are not interchangeable
with sitewise charge, spin or doublon RMS errors. Timing ratios likewise do
not establish matched-accuracy or end-to-end quantum advantage.

## Publication Boundaries

The GitHub audit found public cuprate main at `d9d5481` (7 July), and private
Nighthawk main at `e7faf39` (12 September). The private repository already
contained `cuprate_2d_fermionic_dynamics.py`, `cuprate_2d_fermionic_mapping.py`,
`cuprate_2d_tflo.py` and `benchmark_fermionic_6x6_mps.py`. October results were
not in that September snapshot. These are before-update audit identifiers.

Do not publish the full research working tree into the public historical
repository, change repository visibility, or replace old results with new
ones. Add explicit dated corrections and cross-links while preserving their
original URLs, job identities, data and failed controls. The private
Nighthawk archive remains access-controlled.
