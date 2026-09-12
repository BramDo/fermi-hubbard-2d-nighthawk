# Exact exponential connection: central 3x3 doublon through degree four

<!-- ASSERT_CONVENTION: natural_units=lattice, state_normalization=non-relativistic -->

**Completed:** CENTRAL_DOUBLON_EXPONENTIAL_PILOT_KERNEL_VERIFIED.
All 66 pilot theorems passed the transitive dependency audit. This includes
37 additional theorems beyond the earlier 29-theorem finite certificate.
Three deliberately false claims were rejected by exact arithmetic.

## Precise result

The Hamiltonian is the existing concrete open 3x3 Hubbard matrix with t=1,
t'=-1/4, U=8, mu=0, four up and four down particles. The initial Fock state
has masks (325,170), and the central site is index 4. Evolution has the
Schrödinger sign exp(-iTH), with hbar=1 and time in inverse hopping units.

For the actual central doublon projector D_4 and this initial state s0, define

    F(T) = (exp(iTH) D_4 exp(-iTH))[s0,s0].

For every real T the Lean theorem exact_expectation_hasSum proves that

    sum_{n>=0} T^n c_n = F(T),

with a genuine HasSum statement, not just a formal power-series definition.
The coefficients are explicit Cauchy sums of powers of the concrete matrix.
The following values are checked without extra hypotheses:

| Power | Exact coefficient |
|---:|---:|
| 0 | 0 |
| 1 | 0 |
| 2 | 0 |
| 3 | 0 |
| 4 | 1 |

matches_archived_even_prefix identifies the 0,2,4 entries with the stored
rational prefix [0,0,1]. The external audit checks that the literal prefix
agrees with the actual archived JSON. exact_series_split additionally proves

    F(T) = T^4 + sum_{n>=0} T^(n+5) c_(n+5).

The infinite sum is over complex matrix elements. Summability is supplied by
the exponential-series theorem and retained under continuous evaluation and
finite-prefix removal. No divergent-tsum default or numerical expm solver is
used as a proof oracle. The size of the tail is NOT bounded in this pilot.

## How the chain is connected

| Step | Formal connection |
|---|---|
| Actual Hamiltonian | Gplus=(i/4) HC4=i complexH and Gminus=(-i/4) HC4=-i complexH |
| Actual observable | DC equals the diagonal matrix of siteDoublon 4 |
| Analytic evolution | Absolutely convergent exponential series and noncommuting Cauchy product |
| Scalar expectation | Continuous additive evaluation at the actual initial-state matrix element |
| Concrete coefficients | Matrix moments of the same H4 and projector, using the previously verified sparse path/matrix bridge |
| Stored data | Exact equality to the archived central-site prefix at orders 0,2,4 |

The (2,2) integer matrix moment is 1024. The fourth coefficient is
6*1024/(4^4*24)=1. Moments with either exponent zero or one vanish because
the central projector annihilates the initial vector and its first image.
Thus terms involving third and fourth matrix powers do not need to be
numerically enumerated for this particular coefficient.

## Actual compiler and audit output

Existing WSL Ubuntu-Preview-C environment:

```text
/usr/bin/python3 run.py AnalyticPilot SparsePilot CoefficientPilot MatrixPilot ProjectionPilot MomentPilot DynamicsPilot
REUSED AnalyticPilot
REUSED SparsePilot
REUSED CoefficientPilot
REUSED MatrixPilot
REUSED ProjectionPilot
REUSED MomentPilot
DynamicsPilot 0 19.62
MODULES_COMPILED_NOT_YET_FINAL_AUDIT .../evidence/20260910T170904758337Z

/usr/bin/python3 audit_dynamics.py
DynamicsAudit 0
WrongDynamicFourth 1
WrongDynamicSecond 1
WrongBinomialFactor 1
{"status": "CENTRAL_DOUBLON_EXPONENTIAL_PILOT_KERNEL_VERIFIED",
 "theorem_count": 66, "additional_theorems_since_finite_pilot": 37,
 "certified_coefficients": ["0", "0", "0", "0", "1"],
 "pilot_connected_to_exact_exponential": true,
 "negative_controls_rejected": 3}
```

Only successfully compiled, source-fingerprinted and binary-hashed modules
were reused. The final positive module had no warnings. The final dependency
audit took 20.22 seconds; these times exclude previous attempts and are not
a QPU/classical speed comparison.

Dependency set for every named theorem is a subset of propext,
Classical.choice and Quot.sound. No sorryAx, custom axiom, native_decide or
bv_decide is accepted. The ordinary Lean kernel checks the final terms.

## Level 5: independently executed numerical and symbolic checks

Command:

```text
/home/bram/.venvs/qiskit/bin/python -B check_dynamics.py
status: EXPONENTIAL_PILOT_NUMERICAL_AND_SYMBOLIC_CHECKS_PASSED
dimension: 15876
nonzero matrix entries: 368046
```

| T | Independent sparse exp(-iTH) central doublon | T^4 | Ratio F(T)/T^4 |
|---:|---:|---:|---:|
| 0.005 | 6.248728455701325e-10 | 6.25e-10 | 0.9997965529122119 |
| 0.01 | 9.991865131316098e-9 | 1e-8 | 0.9991865131316098 |
| 0.02 | 1.5948013894974212e-7 | 1.6e-7 | 0.9967508684358882 |

State norms were 1.0, 1.0000000000000002 and 1.0000000000000004.
The independent builder uses full-18-bit annihilation/creation signs, the
same independently written builder from check.py, not the archived propagator
or convolution helpers. The numerical matrix is exactly transpose-symmetric.

SymPy's noncommuting two-level example gives -T**4/3 + T**2 for the low-order
series, agreeing with sin(T)^2. A commuting diagonal Hamiltonian leaves the
observable unchanged. The earlier U=0 and removed-diagonal-hop controls also
remain valid. The numerical/symbolic checks passed in 2.383 seconds excluding
process startup; this is validation timing, not a quantum-advantage benchmark.

These floats are not rigorous enclosures. The inferred next-order behavior is
consistent with the archived -293/36 coefficient, but that coefficient is not
Lean-certified here. The leading T^4 term alone remains insensitive to U.

## Dependencies and resolved proof-engineering failures

With user approval, the official cache retrieval downloaded 15 missing files
and decompressed one already-cached file. Lean stayed at 4.33.1, compiler
commit 819816b2e0a3bf405af45ae5c7af2491d8f5bee6; Mathlib stayed at
0df444a360eaa60ab8c11dca51a86af692955474. No Qiskit packages or global settings
were changed.

The central type mismatch was between canonical matrix instances and those
induced by the operator norm. The pinned Mathlib file
Mathlib/Analysis/Normed/Algebra/MatrixExponential.lean, beginning at line 129,
uses a local backward.isDefEq.respectTransparency=false setting for the same
kind of bridge. We use that setting only on exact_expectation_hasSum. It
affects elaboration of definitionally equal instances, not kernel checking,
mathematical hypotheses or the admissible axiom set.

Other preserved corrections concern scalar-factor ordering, explicit
complex casts, continuous matrix-element evaluation, and avoiding premature
expansion of matrix products. No target coefficient was weakened or changed.

Initial negative tests using decide +kernel did not reduce their complex or
rational decision instances. The harness rejected those as invalid tests;
they were not counted as successful negative controls. The final tests use
norm_num and genuinely leave the false proposition as the failed goal.
They reject a fourth coefficient of 2, a quadratic coefficient of 1, and
omission of the fourth-order binomial factor 6. All earlier logs are retained.

## Evidence and remaining scope

Compilation: evidence/20260910T170904758337Z.
Successful audit: dynamics-audits/20260910T171711968539Z below that directory.
Receipt SHA256:
bb0e8b5a59c9c3ef5bb27b594055bbfd2a79ae0cc90dd162d1bad3587aec1938.

latest-dynamics-verification.json selects the receipt; cache-evidence/ and
dynamics-checks/ retain the dependency and independent-check outputs.
VERIFICATION.md and latest-verification.json retain the earlier finite-only
certificate, whose then-open analytic step is superseded by this result.

Still open: remaining archived coefficients, other observables and site
symmetries, a rigorous useful remainder bound for P4, the general Cauchy-to-
commutator coefficient identity needed to reuse the earlier degree-108 tail
certificate, and the full degree-108 data-to-dynamics certificate. The earlier
2.529e-13 bound is not a bound for this degree-four polynomial.

No hardware run, noise-mitigation fit, physical measurement-accuracy claim,
quantum-advantage proof, publication or Git push occurred. QPU usage: zero.
