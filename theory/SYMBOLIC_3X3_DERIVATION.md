# Symbolic time formulas for the full 3x3 Hubbard instance

Scope: the same complete fixed sector as the numerical reference, dimension
15,876, N_up=N_down=4, centre hole, open 3x3 lattice, t=1, t'=-1/4, U=8, mu=0.
Time T is symbolic; the Hamiltonian parameters and initial product state are
fixed. No fit to previously computed observables is used.

## Equation registry (before implementation)

| ID | Equation | Implementation | Meaning |
|---|---|---|---|
| S1 | A=4(H-16 I) | integer operator construction | A has exact integer entries; shifting H only changes a global phase |
| S2 | v_0=psi_0; v_(n+1)=A v_n | integer_powers | all vectors have arbitrary-precision integer entries |
| S3 | O(T)=sum_m c_(2m) T^(2m) | observable_series | odd coefficients vanish because H, diagonal O and psi_0 are real |
| S4 | c_(2m)=(-1)^m sum_(a=0)^(2m) [(-1)^a binomial(2m,a) v_a^T O v_(2m-a)] / [4^(2m) (2m)!] | observable_series | exact rational coefficients, obtained by multiplying the two exponential series |
| S5 | P_(O,N)(T)=sum_(2m<=N) c_(2m) T^(2m) | evaluate_series | a finite polynomial, not the exact infinite-time function |
| S6 | B=max_i sum_j abs(A_ij)/4 >= norm(H-16I)_2 | exact row-sum bound | valid because A is real symmetric |
| S7 | x=2 B abs(T); r=N+2; remainder <= norm(O) x^r/r! / [1-x^2/((r+1)(r+2))] | even_tail_bound | exact rational bound if the denominator is positive; geometric majorant of the even exponential tail |
| S8 | mean_D=(4 D_corner+4 D_edge+D_centre)/9 | derived observables | square-lattice orbit symmetry; no state-space truncation |
| S9 | spin_RMS=sqrt((4 S_corner^2+4 S_edge^2+S_centre^2)/9) | derived observables | S=n_up-n_down, twice physical Sz |

S4 follows from exp(iHT) O exp(-iHT). For k=2m, the phase product is
i^a (-i)^(k-a)=(-1)^(m+a). Pairing a and k-a halves the number of inner
products without approximation. The scalar shift in S1 cancels in every
commutator and observable coefficient.

For S7, repeated commutators obey norm(ad_H^k(O)) <= (2B)^k norm(O).
The exact function is even in T, so the first omitted power after even N is
r=N+2. Successive majorant terms have ratio at most
x^2/((r+1)(r+2)). This yields a computable uniform truncation bound on
abs(T)<=2/5. Charge has operator norm <=2; spin and doublon <=1.
Mean doublon error is bounded by the same unit-observable bound. The reverse
triangle inequality gives that bound for spin RMS when each site spin has it.

## Units and representation

Energies are divided by the nearest-neighbour hopping energy; T is in hbar/t.
Thus H*T is dimensionless with hbar=1. The numerical matrix builder uses only
dyadic numbers 1, 1/4 and integer multiples of 8. Conversion to A is accepted
only if every imaginary part is zero and every scaled entry is exactly an
integer. All subsequent powers and coefficient arithmetic use Python integers
and rational fractions, never fixed-width integer products or floating fits.

The full sector is retained. Grouping basis states by occupations at sites
0 (corner), 1 (edge) and 4 (centre) only batches exact inner-product sums.
It is not a projection or tensor-network approximation. Coefficientwise
particle/spin conservation verifies the use of the three geometric classes.

## Analytically derived tests before computation

1. T=0: corner C=1,S=1,D=0; edge C=1,S=-1,D=0; centre C=S=D=0.
   Total N=8 and total spin=0; norm is exactly 1.
2. A diagonal Hamiltonian and a basis initial state leave every diagonal
   observable constant: all nonconstant coefficients must vanish.
3. H=[[0,1],[1,0]], psi_0=(1,0), O=diag(0,1): O(T)=sin(T)^2.
   Compare exact coefficients with SymPy's series, and repeat after a scalar
   energy shift to test shift invariance.
4. One-hop counting for this 3x3 initial state predicts mean_D coefficient
   16/9 at T^2. Centre charge coefficient is 17/4 and centre spin -15/4;
   corner charge coefficient is -1/16 and edge charge -1. These follow from
   squared hopping amplitudes, not from a numerical data fit.
5. At every computed order, norm=1, 4 C_corner+4 C_edge+C_centre=8 and
   4 S_corner+4 S_edge+S_centre=0 as exact rational identities.

After construction, evaluate at exact rational T=1/10,1/5,2/5 and compare
against the saved numerical Hamiltonian reference. Keep truncation bounds,
low-order convergence, coefficient-construction time and evaluation time
separate. A finite Taylor polynomial is not a compact closed sin/cos solution
of the full interacting model; the infinite series is exact.
