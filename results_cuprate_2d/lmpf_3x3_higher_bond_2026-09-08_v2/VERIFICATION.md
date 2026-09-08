# Higher-bond verification

Executed commands in the existing WSL Qiskit environment:

```sh
python -B lmpf_2d/verify_higher_bond.py results_cuprate_2d/lmpf_3x3_higher_bond_2026-09-08_v2
python -B lmpf_2d/verify_higher_bond.py results_cuprate_2d/lmpf_3x3_canonical_refine_2026-09-08_v1
```

Selected actual audit output:

```text
D2BP diagnostic:
  status: HIGHER_BOND_SAVED_EVIDENCE_VERIFIED
  fits_checked: 36
  maximum_gram_reconstruction_error: 2.7755575615628914e-16
  maximum_optimizer_projected_gradient: 1.3877787807814457e-16
  local_stability_flags_pass: false

Canonical refinement:
  status: HIGHER_BOND_SAVED_EVIDENCE_VERIFIED
  fits_checked: 18
  maximum_gram_reconstruction_error: 1.1102230246251565e-15
  maximum_optimizer_projected_gradient: 1.5726352511902242e-16
  local_stability_flags_pass: false
```

These are executed NumPy/quimb checks of saved outputs and classification,
not Lean proofs or certificates of physical convergence. No validation errors
were discarded. The native path topology was checked from the actual circuit
gates. Independent canonical tests compare full-bond small operators with dense
Heisenberg evolution, check the chi1 limit, and reject non-neighbour gates.

The native chi4 ideal-operator cross-check is NOT exact agreement: its relative
HS difference is approximately 0.03987. The same initial-state expectation
alone does not establish equality of operators. See the full report for this
qualification, the selected-observable scope and the unchanged 6x6 no-go.
