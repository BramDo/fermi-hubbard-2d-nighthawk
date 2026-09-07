# PA ancilla pilot (offline, 2026-09-06)

User selected PA. No provider calls, paid work, new QPU authorization, or chi=128.
Existing hardware/classical archives and their source files remain unchanged.

## Fixed problem and predictions, before running

Spinful open 6x6 t-t'-U Hubbard: 72 modes, 32 particles, t=1, t'=-0.25,
U=8, mu=0, T=0.4, two symmetric steps. Units: hbar=t=1.
PA uses two data qubits plus one auxiliary per site (108 total).
Prediction: local Pauli weights replace long Jordan-Wigner routing strings;
native depth is NOT inferred from paper fSIM layer counts.
The rectangular 18x6 PA drawing does not directly fit a 10x12 processor.
Encoding overhead and hardware routing may erase the evolution-depth gain.

Reference: Algaba et al., Quantum 8,1327 (2024), arXiv:2302.01862v3,
sections 4,5.2,6. Implement a consistent PA edge-operator gauge, tested
algebraically, not a claim to reproduce the optimized 35-fSIM-layer schedule.

## Equation registry

E_ij = -i gamma_i gamma_j; E_ji = -E_ij; V_i = Z_i.
Adjacent edges anticommute; disjoint edges commute.
Composite edge E_ik = i E_ij E_jk.
S_cycle = i^L product(E_edges); its code sector is S_cycle=+1.
n_i=(1-V_i)/2.
hop_ij = i (V_j-V_i) E_ij /2.
H = sum(c_ij hop_ij) + U sum(n_up n_down) - mu sum(n_i).
Circuit convention: exp(-i H duration); Pauli rotation angle=2*c*duration.

PA gauge: site x has left/right data and right auxiliary A.
T_x=X for even x and Y for odd x; opposite T is Y or X.
Internal edge: T_x(left) opposite(T_x)(right).
Horizontal external edge: T_x(right) Z(A) T_x(next left).
Vertical edge: T_x(right,y) Y(A_y) X(A_y+1) T_x(right,y+1).
Spin order alternates across site columns; original mode labels stay explicit.

## Decisive checks / limitations

1. Exact integer Pauli algebra on 2x2,2x3,6x6; independent cycle rank.
2. Prepare ancillas in all loop-stabilizer +1 sectors for the chosen occupations.
   Boundary gauge degrees may be fixed arbitrarily, but must pass dynamics checks.
3. Construct the complete small even-parity encoding isometry by Majorana edges,
   independently compare every mapped Hubbard term with occupation-basis JW.
4. Compare small encoded circuit evolution against same-event JW evolution,
   including arbitrary even-parity input; check number and loop conservation.
5. Two orderings: original network physical events (same ideal finite circuit)
   and a new disjoint-support-layer palindrome (different finite circuit).
   Never reuse old classical reference for a changed noncommuting order.
6. Count preparation, evolution, full native CZ circuit separately. Verify
   every native CZ edge and output measurement map on the saved backend.
7. No inference of measured fidelity, quantum advantage, or end-to-end speed.

Bounded local work only: small statevector <=12 encoded qubits in first pilot,
transpilation <=108 logical/120 physical qubits. Save tests, circuits, source
hashes, failed candidates and the full report. No automatic hardware submission.
