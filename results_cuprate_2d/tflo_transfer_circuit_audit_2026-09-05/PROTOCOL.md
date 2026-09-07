# Local TFLO transfer, routing and Trotter audit

Status: local work only; no provider calls or new QPU authorization. Preserve
all previous raw data, protocols, analyses and both submission locks.

This is exploratory: the existing U=8 hardware outcomes and preliminary
contrast/error-budget diagnostics have already been inspected. No candidate
is promoted to a new primary result or a validated future hardware method.

## Frozen scope and expectations

- Same 3x3 one-hole model, N_up=N_down=4, t=1, t_prime/t=-0.25, U/t=8,
  open boundaries, spin-interleaved row-major modes; hbar=1.
- Compare three fixed U=0-trained models: current linear-linear TFLO,
  affine TFLO without a time feature, and a classical reference-only linear
  time fit. Ridge is 0.001 throughout; no hyperparameter scan or clipping.
- Six U=0 training points only; two U=0 validation points excluded from
  fitting. U=8 is evaluation-only. Report every model, no U=8-based selection.
- Fixed sector tolerance 1, minimum 32 retained shots, 400 common
  twirl/shot bootstrap replicates, seed 2026090551. Compare both targets and
  all 27 Z/onsite-ZZ observables. Contrast is U=8 minus same-time U=0;
  the U=0 contrast counterparts are training points, not independent holdouts.
- Include ablation of the current TFLO U=8 input: substitute the same-time
  U=0 noisy input, keeping the fitted model fixed. Measure whether using the
  actual interacting input improves target MSE. Bootstrap refits U=0.
- Expect possible transfer bias: previously observed spin RMSE at T=0.4
  was 0.205 against an RMS bootstrap standard error near 0.034. This is a
  diagnostic hypothesis, not proof that shots can never help.
- Routing candidates: unchanged all-pairs reversal network and sparse
  same-operation-order routes left/right/look4/look12. No Hamiltonian term
  or fermionic sign may be dropped. All routing permutations are undone.
- Compile unbound templates in the same CZ/RZ/SX/X path basis, seed 9,
  optimization level 3. No binding-specific simplification. Compare CZ
  count, two-qubit depth and timing from the saved calibration snapshot;
  this is not a new live timing quote or a measured fidelity improvement.
- For the minimum-CZ candidate (tie: two-qubit depth then name), also
  compare eight twirled/readout-masked, one-qubit-cleaned physical templates.
  Fresh masks are saved: different CZ counts consume the twirl RNG differently.
- Check full 2x2 operator equivalence and full 18-qubit states at both U=8
  target times. T=0 and U=0 are limiting cases. Save failed candidates;
  never declare one equivalent after a failed test.
- Trotter test: U=8 at T=0.2 and 0.4, 2/4/8 steps at fixed total time;
  compare with sparse exact fixed-sector Hamiltonian evolution. Validate
  Hamiltonian construction independently, norm, sector and time composition.
  U=0 uses the exact FLO finite-circuit reference and an independent sparse-H
  reference. Expect roughly fourfold error reduction when doubling steps;
  the old T=0.2 two-step spin Trotter RMSE was about 0.00584.

## Equation registry and code units

| ID | Equation | Code | Units/convention |
|---|---|---|---|
| fit | y=m*x+c*T/Tscale+b or y=m*x+b | fit_models/predict | Pauli values dimensionless; Tscale=0.5 |
| contrast | Delta O=O(U=8)-O(U=0) | audit contrasts | same time, observable and sampling blocks |
| mse | mean((prediction-reference)^2) | MSE/paired gains | equally weight sites and both target times |
| routing | FSWAP=SWAP*CZ; conjugate mode labels with each F | sparse_template | preserve full fermionic parity |
| hop | exp[-i*c*(a_p^dag a_q+h.c.)*dt/2] | half_gate | XXPlusYY angle c*dt on adjacent slots |
| onsite | exp[-i*U*n_up*n_down*dt/2] | half_gate | CP angle -U*dt/2 |
| exact | psi(T)=exp(-i*H*T)psi(0) | expm_multiply | t=1, hbar=1; T is not QPU wall time |
| error | norm(psi_n-phase*psi_exact) and observable RMSE | trotter | phase-aligned state, un-clipped observables |

Tests before production: identity-noise TFLO, exclusion of target references,
T=0 preparation, U=0 limit, complete 2x2 operator comparison, and signed
fermionic hopping/original-network equivalence. References and all original
hardware hashes must be verified before their reuse.

Interpretation: sampling intervals exclude model-transfer bias and hardware
drift; a small 3x3 result cannot establish quantum advantage. Fewer CZ gates
may trade off against longer depth. Do not infer hardware accuracy from a
noiseless circuit comparison.

Source context: https://arxiv.org/html/2510.26845v2 (TFLO validation caveats,
same-depth training, circuit optimizations and independent classical checks).
