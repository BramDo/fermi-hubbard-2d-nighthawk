# Archived-twirl reuse gate, before new hardware scoring

Offline, bounded structural diagnostic for the eight archived 3x3 twirls of
job daem7r642tqs73autong on ibm_phoenix. Load the 24 provider QPY circuits and
frozen calibration, verify bound/provider identity and measurement layout.
Do not read target bitstrings, fit coefficients, propagate new TN states, run
hardware, publish, or expand to 6x6. Existing results stay unchanged.

Compare each nonzero twirl to twirl0 at each CZ-folding factor. Canonicalize CZ
qarg order only (CZ is symmetric). Compare native gate signatures including
parameters. Also compare per-wire sequences through each wire's final CZ;
this ignores independent-wire scheduling and separates the terminal 1q suffix.
A mismatch there rules out the simple identical-core/terminal-mask mechanism,
not all possible mathematical channel or operator equivalences.

Use the same frozen local depolarizing surrogate as earlier calculations.
For a gate on k qubits with decay exp(-lambda), the normalized log determinant
of its embedded full n-qubit channel is -(1-4^(-k))*lambda. Consequently

    L(E) = log(abs(det(E)))/4^n
         = -sum_g (1-4^(-k_g))*lambda_g.

Derivation: local PTM eigenvalues are 1 and exp(-lambda), the latter repeated
4^k-1 times. Embedding multiplies logdet by 4^(n-k); divide by 4^n. Unitary
conjugations, including ideal readout unmasking and Pauli frame changes, have
absolute determinant one. Determinants multiply without requiring the noisy
channels to commute. The invariant is dimensionless; no huge determinant or
18-qubit superoperator is constructed. At zero noise it is exactly zero.

Differences greater than 1e-10 distinguish the FULL surrogate channels, even
if their ideal physics agrees. This does NOT establish that a particular
Heisenberg operator differs, quantify observable error, or rule out scalar or
other transport of selected operators. Matching determinants would also NOT
prove equivalence. We therefore never authorize weight reuse from this
necessary diagnostic alone.

Independent verification: reconstruct local adjoint channels directly with
2x2/4x4 unitary matrices and trace-orthonormal Pauli matrices, then verify their
log determinants against the formula on all unique archived gate types/rates.
Test an independently composed dense THREE-qubit channel, including reversed
CZ qargs, coherent noncommuting gates and final readout-X masks. Independently
parse calibration gate errors rather than call FrozenSurrogate.rate in audit.
Audit all native circuits, per-wire core comparisons and saved input hashes.

If reuse is not established, save the negative diagnostic. Prepare one next
twirl (ID1, chosen by fixed order, not its measured accuracy) for separately
computed central operator Grams. Do not launch a seven-twirl high-bond batch.
No fit or matching-accuracy conclusion is justified before that computation.

