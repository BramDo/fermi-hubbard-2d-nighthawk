# Exact ideal-Pauli norm: bounded offline follow-up

This follow-up is specified after inspecting the prior ZZ component diagnosis.
It is not a blinded preregistered experiment or independent data validation.
Preserve all prior data, failed raw-Gram flags, and the nonmonotone ideal ZZ
expectation. No chi increase, TN propagation, QPU job, hardware-weight application,
6x6 run or publication. Use only the three central operators at twirl0:
Z_up and Z_down at chi64/128, ZZ at chi128/256, same archived 3x3 native inputs.

For dimension d=2^18, O=Z8, Z9 or Z8 Z9 and the ideal unitary U, A=U^dagger O U
satisfies A^dagger A=I, hence Tr(A^dagger A)/d=1. Pauli readout-mask signs square
to1. Physical preparation gates are included; measurements are excluded from
the unitary channel. Verify the actual archived native gate matrices and check
the trace identity independently with exact small symbolic matrices.

In a separate copied Gram matrix replace only F00 by1. This is not rescaling
the approximate operator, setting a measured particle count, or changing noisy
norms. G=F[1:,1:] and b=F[1:,0] must remain bit-identical. Reject invalid/non-PSD
input before substitution; require the canonical approximate F00<=1 up to
roundoff. Increasing only that diagonal preserves PSD for these inputs.

The objective is F00 - 2*b^T*c + c^T*G*c + ridge*||c||^2, with sum(c)=1.
F00 is constant in c: both unregularized and fixed-ridge1/56 coefficients must
be unchanged. The projection residual must increase by exactly1-F00, so no
smaller residual or improved hardware expectation may be claimed from this
substitution. With unchanged c, any fixed mean/covariance estimate is unchanged.

Follow-up local numerical gate (not a rigorous truncation error bound):
- exact-F00 full-Gram relative Frobenius change <=1%;
- G relative Frobenius change <=1%, and b relative L2 change <=1%, separately;
- fixed-ridge coefficient L1 change <=0.05;
- PSD, finite values, unchanged G/b/weights and consistent residual shifts.
The separate block checks prevent a large known F00 from hiding changes in
small noisy blocks. Preserve the original raw-Gram gate alongside this gate.
These are diagnostics on existing snapshots, not certification of their error.

Use the existing offline WSL environment, one-thread BLAS/OpenMP. Run the prior
36 tests and new symbolic/invariance/rejection/block-sensitivity tests. Archive
the input JSONs and source hashes, not another copy of large tensor arrays.
Independently reconstruct the classification and solve the equality-constrained
fit with a direct KKT system, separate from the production null-space solver.
Keep source/model, shot/calibration and tensor-truncation uncertainties separate.
Full 27-operator/eight-twirl, device-noise and hardware-quality validation remain
open even if this necessary central-operator gate passes.
