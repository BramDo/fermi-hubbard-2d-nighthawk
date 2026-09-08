# Offline chi=2/4 stability test, 3x3 native circuits

User approved the next offline step, not a new QPU job. Existing job:
daem7r642tqs73autong on ibm_phoenix, native 18 active wires, U8, T0.4,
two product-formula steps. Preserve all earlier 3x3 no-go evidence.

First diagnostic: central-site Z_up, Z_down and ZZ (Pauli indices 8,9,22),
fixed twirl 0. Evaluate the ideal arm and actual CZ-folded arms 1/2/3 at
chi=1,2,4. The three observables are selected by location, not by observed
mitigation improvement. A one-twirl test is not the full eight-twirl estimator.
Do not reuse these coefficients on the averaged hardware records.

Same normalized Hilbert-Schmidt conventions and per-native-gate surrogate as
the previous run. Noise after physical gates, physical preparation included,
readout-X-mask sign removed. Reuse hashed chi=1 product checkpoints; compute
new chi=2/4 states with the existing 2D D2BP code. Save each completed state
as numeric arrays plus explicit indices/tags/exponent, without pickle.

For F_ij=inner(O_i,O_j), check both loop-corrected BP and resource-bounded
exact contraction of the same truncated TN. Exact contraction is a diagnostic
on this graph, not a guarantee of scalable full-paper reproduction. No rejected
loop result is silently replaced with an accepted loop coefficient.

Necessary local stability flags, NOT a convergence proof:
- Relative Frobenius change F(2)->F(4) <= 1%.
- L1 change of fixed-ridge coefficient vector <= 0.05.
- Finite, PSD Grams and zero unconverged propagation updates.
Also report unregularized coefficients, ideal-TN expectations versus the exact
finite-circuit reference, and whether the local diagnostic passes every flag.
Ridge remains 1/56; no fitting to the reference values or hardware means.

Budget: 1200 local seconds, one-thread BLAS; each scalar contraction is guarded
at 2^22 intermediate elements and 2e9 estimated FLOPs. Do not allocate 4^18
dense operators. If the diagnostic fails, record the failure and diagnose it;
do not begin the full 27-observable/eight-twirl or 6x6 calculation.
