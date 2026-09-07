# Bonsai local fixed-target pilot, 2026-09-06

User approved the proposed next local Bonsai comparison. No hardware use,
credentials, qDRIFT, new time cutoff, shots or chi=128.

Target: full open spinful6x6,72 modes,32particles,t=1,t'=-0.25,U=8,
mu=0,T=0.4,two symmetric steps. Preserve network_events exactly.
Sources: Miller et al., arXiv:2212.09731; Esposito et al.,
arXiv:2608.25024, II.1-3 and appendix C. Not a reproduction of Boston.

## Predictions before runs

A hardware-subgraph ternary tree should reduce fragmented hopping support.
Fock preparation should need X gates only, without encoding ancillas.
Annealing Majorana-PAIR assignments should lower a native-gate cost proxy,
but may not lower critical-path depth. No win assumed before compilation.
The actual native CZ trace, duration and output parities decide the result.
Our deterministic product formula visits all nonzero terms equally often;
do NOT copy Boston's coupling-weighted qDRIFT cost or hardware noise weights.

## Equation registry and conventions

Majorana pair at a tree node: follow root prefix, X (or Y) branch, then Z
branches until a leg. Ignore the all-Z leg. Each resulting Pauli squares toI;
all2n strings anticommute. gamma_even=a+a^dagger; gamma_odd=i(a^dagger-a).
V_i=-i gamma_2i gamma_2i+1; n_i=(1-V_i)/2.
hopping(p,q)=i*(gamma_2p gamma_2q+1 - gamma_2p+1 gamma_2q)/2.
onsite(p,q)=(I-V_p-V_q+V_p V_q)/4.
Evolution=exp(-i*angle*operator), hbar=t=1. Retain identity/global phases.
V_i must be positive pure-Z strings with an invertible GF(2) parity matrix.
Classical decoding n=A*b mod2; Fock preparation b=A^-1*n mod2.
Fock-state phases are tracked in small full-Hilbert-space isometry tests.

For native Pauli rotations use a connected Steiner tree in the saved qubit
graph. Reduce Z support to one root using adjacent CNOT conjugations,
apply RZ, undo ALL conjugations. Steiner wires are arbitrary quantum data,
not initialized/discarded ancillas. A one-bit parent with one-bit child
needs CX(child,parent); a zero-bit parent first needs CX(parent,child).
This must be proved numerically on arbitrary small full states.

## Scope and acceptance

New source files and frozen outputs only. Existing sources/archives untouched.
Use established WSL Qiskit2.5.2, CPU only, bounded runs (<=600s each).
Test complete2x2 operator equivalence, all Majoranas, GF2 decoding,
number/doublon observables and same-event evolution including nonzero mu.
Check larger algebra and all hardware CZ edges without a72q statevector.
Keep failed candidates. No advantage or hardware-accuracy claim.
Try the original72-qubit subset and one72-qubit rectangle, recording both.
Optimize pair assignments with fixed seeds and bounded local updates.
Rank actual complete native circuits separately by CZ count and duration;
a lower proxy alone is not success.
