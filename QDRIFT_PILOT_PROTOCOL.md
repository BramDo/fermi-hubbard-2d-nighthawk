# First qDRIFT estimate and exact small-system pilot

User requested qDRIFT first, including an estimate of possible improvement.
New local tests only. No QPU use, package installation, provider connection,
new hardware authorization or chi=128. QDrift already exists in Qiskit2.5.2.

## Fixed physics and predictions before computing

Full6x6:72 modes,32particles,t=1,t'=-0.25,U=8,mu=0,T=0.4.
qDRIFT approximates exp(-iHT), not the old two-step product formula.
Never present old-circuit equivalence or old chi64 results as an exact reference.
Expected Pauli coefficient1-norm after removing identity: lambda=145+216=361.
Expected identity coefficient:72. For number-conserving groups, lambda=145+288=433.
Sampling fewer operations should lower native resource counts, but may increase
algorithmic bias. No hardware accuracy improvement is presumed.

## Definition / equation registry

H=c0 I+sum_j w_j A_j, w_j>0, ||A_j||=1.
p_j=w_j/lambda, lambda=sum(w_j); sample N indices independently.
V_sample=exp(-i c0 T) product_k exp[-i(lambda*T/N) A_jk].
Two arms: individual signed Pauli strings and complete number-conserving
hopping/onsite groups. Group exponentials are synthesized exactly.
Use the saved Bonsai XYZ/count assignment and same72-qubit rectangle.

Worst-case reference scaling is N~2(lambda*T)^2/epsilon, not a promise of
observable accuracy and not a lower bound on practical N.
The cited tighter-bound paper arXiv:2506.17199 Theorem1 contains E(T/r)^(r Gamma):
its actual channel repetitions are r*Gamma, so substituting r for physical N
in its linear expression is not justified. Do not claim a linear-lambda
physical-gate guarantee from that expression. Record this normalization caveat.

## Computations and limits

1. Cross-check explicit-N sampling against the installed Qiskit QDrift on a toy.
   Qiskit reps is NOT the desired count: N=ceil(2 lambda^2 T^2 reps).
2. Exact2x2 doped initial state (3 particles), full t-t'-U, T=0.4.
   Compare to an independent dense occupation-basis exp(-iHT), and record the
   old two-step circuit error separately.
3. Simulate256 independent noiseless random circuits for N=16,32,64,128,256,512.
   Evaluate ensemble charge, spin and doublon RMSE, particle number and leakage.
   Inter-circuit Monte Carlo uncertainty is not shot noise or hardware noise.
   A single random circuit with more shots does not eliminate qDRIFT sampling error.
4. Compile6x6 resource examples for N=128,256,512,1024, both arms, fixed seed.
   Retain all phases, signs, t-prime, U and T. Count prep/readout/twirl.
   Resource samples are not a complete hardware/ZNE ensemble.
5. Small-system error is not a6x6 accuracy certificate; record lambda*T/N and
   do not transfer results at the same N to a much larger Hamiltonian.
6. Guard local runtime and RSS. Freeze source, configuration, seed, outputs,
   exact reference and hashes. Leave all old archives untouched.

Sources: arXiv:1811.08017, arXiv:2506.17199 (Theorem1),
arXiv:2608.25024 (AppendixB), IBM Qiskit QDrift documentation.
