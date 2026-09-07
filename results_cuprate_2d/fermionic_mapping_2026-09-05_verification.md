# Offline mapping verification - 2026-09-05

`verify_cuprate_2d_mapping_archive.py` completed successfully in the established
WSL Qiskit environment. It made no IBM service calls and submitted no jobs.

- 31 archived files passed SHA-256 verification, including all 13 QPY files.
- Four validated source-file hashes matched the working source.
- All 34 numerical checks in `validation.json` passed.
- The saved 2-, 4-, and 8-step circuits each have 72 logical modes and 108
  mapped observables; the 120-qubit QPY width includes unused backend wires.
- Every native CZ uses an edge of the captured Phoenix coupling map.
- Each selected physical path is injective and adjacent; each final layout
  matches its initial layout and the logical fermion order is restored.
- Observable Pauli records match the saved QPY layout exactly.
- Plans remain unsubmitted with future settings of 512 shots per noise factor,
  noise factors 1/3/5, and maximum execution time 5 seconds. Whether a folded
  experiment can finish within that cap is not established by compilation.

## Numerical interpretation

The adaptive route preserves the original symmetric product formula to about
1e-14 in the tested full small-lattice unitary. The selected parallel network
preserves the full Hamiltonian but changes the second-order term ordering.
Its small-lattice refinement ratios are approximately four when dt is halved
at fixed total time. No corresponding 6x6 convergence claim is made.

For the doped 2x3 test at dt=0.1 and total time 0.8, comparison to independent
exact Hamiltonian evolution gives:

| circuit ordering | charge RMSE | spin-z RMSE | double-occupancy RMSE |
|---|---:|---:|---:|
| original symmetric reference | 0.00119663 | 0.00415197 | 0.00114491 |
| parallel network | 0.00113115 | 0.00256891 | 0.00062363 |

This is not uniform dominance: the network charge error is larger in several
other small-lattice/time cases. All cases are retained in the validation JSON.
Native compilation equivalence was checked on the small path circuit, not
by a full 72-qubit state-vector calculation.

The two-step native count falls from 67,793 to 15,400 CZ gates (77.28% fewer)
and depth from 63,098 to 1,853 (97.06% lower, a 34.05-fold depth ratio).
The original formula at optimization level 3 alone still needs 60,646 CZ
gates and depth 59,271. The best tested adaptive route, which retains that
formula exactly, needs 20,944 CZ gates and depth 8,822.

The selected network is best among the tested candidates under the declared
two-qubit-depth objective; it is not proven globally optimal. These are
compilation improvements, not measured hardware accuracy or quantum advantage.
The old shallow hardware/MPS results are not a baseline for this full model.
