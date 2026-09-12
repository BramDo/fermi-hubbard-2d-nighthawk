# Independently checking the 3x3 central-doublon certificate

This directory is a standalone Lean project for the result described in
[From Quantum Dynamics to Mathematical Proof](https://edukaizen.nl/2d-local-quantum-advantage-en/lean-certified-quantum-dynamics/).
The repository is private: readers need repository access to clone it.

## Verified clean run, 12 September 2026

- All 145 project modules were rebuilt; zero old project binaries were reused.
- The audit covers 2,313 named project theorems, including the original 66
  pilot theorems and the many prerequisite Hamiltonian/row lemmas.
- Every audited dependency set is within propext, Classical.choice, Quot.sound.
- Three deliberately false claims were rejected; the independent integer,
  numerical/symbolic checks and seven packaging tests passed.
- [Audit and build receipt](evidence/rebuild/verification.json),
  [printed axioms and final statements](evidence/rebuild/Audit.txt),
  [numerical cross-check](evidence/rebuild/numerical-check.json).

The complete build took about 41 minutes on this local setup. This is proof
verification time, not a classical dynamics benchmark or a QPU comparison.

## The exact claim

For the concrete open 3x3 Hubbard model with t=1, t'=-1/4, U=8, mu=0,
hbar=1, four particles of each spin, and initial masks (325,170), the
central-site doublon expectation is

    F(T) = <psi0| exp(iTH) D4 exp(-iTH) |psi0>.

Lean establishes, for every real T,

    F(T) = sum(n >= 0) c_n T^n,
    c_0 = c_1 = c_2 = c_3 = 0, c_4 = 1,
    F(T) = T^4 + sum(n >= 0) c_(n+5) T^(n+5).

The last sum is convergent. This pilot does not bound its size, certify all
605 archived coefficients, or prove hardware accuracy or quantum advantage.
The leading coefficient alone is insensitive to U; removing diagonal hopping
does change it.

Start with these definitions and theorems, not the theorem count:

- [DynamicsPilot.lean](DynamicsPilot.lean): expectation, scalarCoefficient,
  generator_plus, generator_minus, projector_matches_site,
  exact_expectation_hasSum, coefficient_four, and exact_series_split.
- [ConcreteDefs.lean](ConcreteDefs.lean): finite sector, geometry, fermionic
  hopping action and real Hamiltonian.
- [ConcreteProofs.lean](ConcreteProofs.lean): the concrete fermionic-sign,
  sector and Hermiticity certificate, including the complex Hamiltonian.
- [MomentPilot.lean](MomentPilot.lean): the exact matrix moments.
- [AnalyticPilot.lean](AnalyticPilot.lean): the convergent noncommuting
  Cauchy product used for the matrix-exponential connection.

## Reproduce on Linux or WSL

Prerequisites: Git, Python 3.10 or later, and elan/Lean. Use the versions in
lean-toolchain and lake-manifest.json; do not update to a different Mathlib.

    cd formal/lean
    lake exe cache get
    python3 verify.py --workers 2 --memory-mb 3000

The first command may download the pinned Lean toolchain and upstream
dependencies/cache if they are not already installed. No IBM credentials,
Qiskit account, quantum job, or paid service is required for the proof.
Reserve roughly 6 GB available RAM for two compiler processes; use
--workers 1 on smaller machines. The full concrete model includes 126 row
blocks, so verification takes substantially longer than reading the article.

The verifier compiles all 145 project modules into a NEW empty directory.
It excludes prior project build directories from LEAN_PATH, checks all
package-source hashes and upstream Git revisions, audits every named project
theorem transitively, separately identifies the original 66 pilot theorems,
and rejects three deliberately false claims. Each run preserves its own logs
and verification.json under .verification/.

Expected final status:

    CLEAN_SOURCE_BUILD_AND_TRANSITIVE_AUDIT_PASSED

The only accepted axioms are propext, Classical.choice, and Quot.sound.
Unfinished proofs, extra axioms, native_decide and bv_decide are rejected.
Finite exhaustive goals use decide +kernel. Compiled machine code is not used
as an oracle to establish the reported coefficient.

The original 66-theorem count covers seven pilot modules, not all prerequisite
Hamiltonian lemmas. The new driver also audits those prerequisite theorems.
The final theorem depends on the actual model definitions; it is not a theorem
about an assumed answer.

## Independent numerical checks

The stdlib-only integer check runs automatically in verify.py. It reproduces
the archived central prefix [0,0,1], 16 projected output states, and the exact
integer squared norm 1024, including interference and fermion signs.

An optional independent floating-point and symbolic check requires NumPy,
SciPy and SymPy in a separate Python environment:

    python3 -m pip install -r requirements-numerical.txt
    python3 -B checks/pilot/check_dynamics.py

It constructs the full 15,876-dimensional Hamiltonian and compares the
small-time expectation at T=0.005, 0.01 and 0.02 with T^4. These numerical
checks are separate from Lean's logical proof.
The optional dependency versions match the executed local cross-check.

## Provenance and trust boundary

All 145 Lean source files are unchanged from the local research checkpoint
d97c3b5fb8affc27ad9ba091c636b9aff2ca7f5f. That hash belongs to a different local
repository, not this repository's history. It is retained as provenance;
the GitHub commit containing THIS directory is the retrievable checkpoint.
source-manifest.json maps each file to its original path and SHA-256.

The original report and logs are preserved under evidence/original/.
Their machine-specific paths are historical context, not build prerequisites.
The portable build needs only this directory and its pinned upstream packages.
Fresh rebuild evidence is stored separately under evidence/rebuild/.

The same GitHub checkpoint also preserves the original
[symbolic calculation script](../../run_symbolic_3x3.py),
[derivation](../../theory/SYMBOLIC_3X3_DERIVATION.md), and
[symbolic result archive](../../results_cuprate_2d/symbolic_3x3_2026-09-07_v1/).
Their stored hashes have been checked. The coefficient input here is
byte-identical to that archive. Those full numerical/symbolic records remain
distinct from this low-order Lean certificate; uploading them does not
formally certify all 605 coefficients.

The local clean rebuild reused pinned upstream Mathlib dependency caches,
but no old project .olean files. Lean's kernel, compiler/runtime implementation,
hardware, and standard axioms remain part of the usual trusted foundation;
reproduction by another person on another machine is a further independent
check. The certificate does not certify its Python build driver.
