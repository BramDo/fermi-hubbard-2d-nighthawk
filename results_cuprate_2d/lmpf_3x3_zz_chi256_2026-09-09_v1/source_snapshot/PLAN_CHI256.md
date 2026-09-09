# Central ZZ only: offline chi256 refinement

Reuse the four byte-identical central ZZ chi128 states from
lmpf_3x3_chi128_2026-09-08_v1. Compute only observable 22 (Z8 Z9), twirl 0,
ideal arm and actual CZ-folded arms 1/2/3, from the original observable and
unchanged full native channels. Archived job daem7r642tqs73autong on ibm_phoenix.
The native graph is an 18-wire open chain, although the Hubbard model is 2D.

Keep normalized dimensionless Pauli HS products, physical preparation gates,
readout signs, frozen calibration-derived depolarizing surrogate and ridge 1/56.
The original canonical propagation kernel, cutoff 1e-12 and all historical
drivers remain unchanged. No target/reference-assisted fitting.

Pre-run expectation: the Gram change may shrink from 3.2948% at chi64->128,
but passage of 1% is not assumed. ZZ expectation is positive, about 0.2; exact
finite-circuit reference is 0.22940044217034958. It is only a diagnostic.
No monotonic convergence or infinite-chi extrapolation is assumed.
Fixed necessary flags: relative full-Gram Frobenius change <=1%, and
ridge-coefficient L1 change <=0.05. Never change these after seeing the result.

Resource preflight, n=18, physical dimension 4, chi256:
- bond bound d_i=min(256,4^min(i,18-i));
- sum_i 4*d_i*d_(i+1)=2,761,248 real coefficients;
- raw state storage <=22,089,984 bytes for float64, twice that for complex128;
- exact chain overlap <=2,769,572,160 multiply/add FLOPs and peak 262,144 elements;
- largest two-site SVD matrix <=1024 by 1024 (workspace adds memory).
The old 2e9 contraction-FLOP guard is intentionally increased to 3e9 for this
new scoped driver and auditor only. The memory-element guard stays 2^22.
No dense 4^18 allocation or local chi^4 bra/ket precontraction is permitted.
The raw-TN auditor separately checks its planned tree before executing it.

Preflight requires >=1.5 GiB available memory and >=1 GiB free disk. At inspection
WSL had 6232 MiB available and the C: filesystem about 29 GiB free.
Soft run limit: 1500 seconds, checked between states. Peak RSS is checked between
states against 2 GiB and reported. These are not OS-enforced within-SVD limits.
One-thread BLAS/OpenMP; expected runtime roughly 10-20 minutes, not guaranteed.
Stop at chi256. Save each state and retain partial data or failure if a guard trips.

Run the prior 33 tests plus new preflight/archive tests. Independently reconstruct
all chi128/256 overlaps and four fits, source/output hashes and classifications.
Large new NPZ files remain locally in place. For Git, produce a result-local
archive/manifest.json and SHA256-addressed gzip parts <=9,000,000 bytes,
compatible with scripts/restore_archives.py. Verify decompression and originals;
never commit individual files >=10 MB or overwrite a mismatching restored file.

No new QPU job or hardware weights, no recomputation of Z_up/Z_down, no complete
27-observable/eight-twirl validation and no 6x6 run. Keep truncation, model bias,
projection bias and shot/calibration uncertainty separate. Local flags are not
a rigorous error certificate or validation of the device-noise surrogate.
