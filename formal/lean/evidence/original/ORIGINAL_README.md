# Central 3x3 doublon: exponential pilot verified through T^4

<!-- ASSERT_CONVENTION: natural_units=lattice, state_normalization=non-relativistic -->

Verified continuation: **66 Lean theorems**, comprising the earlier 29 finite
theorems and 37 additional analytic/matrix-dynamics theorems. The pilot now
connects the actual central doublon expectation under exp(-iTH) to a convergent
power series and certifies its coefficients at powers 0,1,2,3,4 as **0,0,0,0,1**.
The even prefix **0,0,1** matches the actual archived coefficients.

The exponential connection is complete for this low-order, single-observable
pilot, not for all 605 archived coefficients. The earlier finite-only evidence
and its limitations remain preserved as historical records. See
ANALYTIC_VERIFICATION.md and latest-dynamics-verification.json for the new audit.

## Fixed model

Open 3x3, t=1, t'=-1/4, U=8, hbar=1, four up and four down particles.
Initial masks are (325,170), with the central site 4 empty. The same concrete
Hubbard model from lean-concrete-hubbard is imported, not replaced by a toy.
H4=4H is the unshifted integer Hamiltonian; time T is in inverse hopping units.
The projector selects states with both spins at site 4.

## What the new proofs establish

| Module | Theorems | Checked content |
|---|---:|---|
| SparsePilot | 6 | The path-entry representation equals every concrete H4 matrix entry; zero/one-step projection vanishes; 32 projected two-step paths; squared combined amplitude 1024; exact normalization |
| MatrixPilot | 8 | Sparse addition/scaling; a valid-support update is actual matrix multiplication; initial basis vector, first power and second power of H4 |
| ProjectionPilot | 8 | Filtering is the central doublon projector; sparse overlap equals the full sector sum; the projected first matrix row vanishes; the projected H4-squared row has squared norm 1024 |
| CoefficientPilot | 7 | Empty overlaps; complete finite Cauchy formulas at orders 0,2,4; their exact values; archive-prefix identity; the degree-four polynomial |
| AnalyticPilot | 6 | Absolutely convergent exponential series, noncommuting Cauchy product, time scaling and exact summed operator |
| MomentPilot | 12 | Symmetry, central projector, vanishing low moments and exact (2,2) integer matrix moment 1024 |
| DynamicsPilot | 19 | Complex matrix conversion, coefficient moments, actual Hamiltonian/projector identification, coefficients 0 through 4, exact expectation series and exact tail split |

Writing v_k for the sparse H4^k initial-state row, the finite calculations give

    P_D v_0 = 0,
    P_D v_1 = 0,
    sum_s (P_D v_2(s))^2 = 1024.

The two-step paths interfere: there are 32 nonzero path contributions but
16 distinct projected output states. The overlap calculation combines paths
to the same state before forming the squared amplitude; it does not add
incoherent path probabilities.

For the fourth Cauchy coefficient all five cross terms are included, with
weights 1,-4,6,-4,1. The zero/one-step projectors eliminate the terms involving
v_3 and v_4, regardless of those vectors. The remaining term gives

    c4 = 6*1024 / (4^4 * 4!) = 1.

Thus the proved finite polynomial is P4(T)=T^4. The factor 4^4 converts H4
to H, and the factorial and binomial factor are explicit in the definition.
The analytic continuation now supplies the missing identification with the
actual exponential expectation, not only the finite Cauchy rule.

## Exact analytic statement

Let F(T) be the initial-state matrix element of exp(iTH) D_4 exp(-iTH), using
the same concrete Hamiltonian and the actual central-site doublon projector.
For every real T, Lean proves convergence and

    F(T) = sum_{n>=0} c_n T^n,
    c_0 = c_1 = c_2 = c_3 = 0, c_4 = 1,
    F(T) = T^4 + sum_{n>=0} c_{n+5} T^(n+5).

The coefficients and equality are formalized over complex matrices/numbers.
No finite numerical propagator or floating-point calculation enters these
theorems. The tail is genuinely summable; this is not use of a default value
for a divergent infinite sum. Its size is not yet bounded by this pilot.

## Independent checks and interpretation

check.py uses an independent full-18-bit implementation of annihilation then
creation, with fresh coordinate-generated bonds and an independently written
coefficient convolution. It imports none of the old generator helpers.
It reproduces the archive's first three D_centre coefficients exactly.

check_dynamics.py additionally builds the full 15876-dimensional sparse
Hamiltonian and evaluates exp(-iTH) numerically at T=0.005,0.01,0.02. The ratios
F(T)/T^4 are 0.99979655, 0.99918651, 0.99675087. This independently supports
the leading term, but is not a rigorous floating-point enclosure. Symbolic
two-level and commuting-operator controls also pass.

Two limiting checks pass:

- U=0 yields the same prefix 0,0,1. The leading term alone is not a test of
  the U=8 interaction; interaction-sensitive terms require higher orders.
- Removing diagonal hopping yields prefix 0,0,0. The current T^4 term is
  sensitive to the diagonal hopping route.

The already proved degree-108 tail bound must NOT be attached to P4. No useful
degree-four approximation error at T=0.4 is certified here. Only one observable
and three of the 605 archived coefficients are targeted, not all 27 local
observables, all coefficients, noise mitigation, hardware accuracy or advantage.

## Evidence and reproduction

Successful finite check and final audit:
`evidence/20260910T155213786847Z`.

Successful analytic compilation: `evidence/20260910T170904758337Z`.
Timestamped analytic audit attempts are stored below its dynamics-audits/
directory; latest-dynamics-verification.json selects the successful one.

VERIFICATION.md and latest-verification.json retain the earlier finite-only
result. ANALYTIC_VERIFICATION.md describes the completed analytic pilot.
All earlier source versions and unsuccessful attempts are retained.
Source fingerprints include local imported modules; compiler-cache reuse
also checks binary hashes. The original 3x3 compiled inputs are checked against
their saved source and binary hashes before each attempt.

Existing WSL Ubuntu-Preview-C, Lean 4.33.1, Mathlib commit
0df444a360eaa60ab8c11dca51a86af692955474:

    /usr/bin/python3 check.py
    /home/bram/.venvs/qiskit/bin/python -B check_dynamics.py
    /usr/bin/python3 run.py AnalyticPilot SparsePilot CoefficientPilot MatrixPilot ProjectionPilot MomentPilot DynamicsPilot
    /usr/bin/python3 audit_dynamics.py

This requires the existing compiled concrete-Hamiltonian certificate in the
isolated Lean project. Without it, reproduce that certificate first. No new
dependencies are installed by these verification scripts. With user approval,
fetch_analytic_cache.py retrieved only 15 missing official cache files and
unpacked one already-cached file, without changing the pinned versions.
Compiler products are ignored
by Git; no source archive is overwritten and no quantum job is submitted.

## Next open step

Extend the concrete moment/coefficient certificate to higher orders, starting
with T^6, then other site observables. The saved next central coefficient is
-293/36, but this pilot does not prove it. Reusing the previous degree-108
commutator tail bound will additionally require the general identification
between the Cauchy coefficients and the existing commutator coefficients.
No claim that the full 605-coefficient or degree-108 dynamics certificate is
already complete follows from this low-order pilot.
