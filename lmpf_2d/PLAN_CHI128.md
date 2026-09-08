# Offline chi128 continuation

Reuse the verified chi64 checkpoints from lmpf_3x3_chi32_64_2026-09-08_v1.
Compute only chi128, from the original input operator and full native channels,
for central operators 8 (Z_up), 9 (Z_down), 22 (onsite ZZ), twirl 0, ideal arm
and actual CZ-folded arms 1/2/3. Job daem7r642tqs73autong, ibm_phoenix.
Preserve the fixed depolarizing surrogate, signs, ridge 1/56, canonical kernel,
and normalized Hilbert-Schmidt convention. No reference-assisted fitting.

Before computing: the observed refinement trend suggests smaller Gram changes
than chi32->64 (1.73%, 1.36%, 7.07%), but neither monotonicity nor passage of
the thresholds is guaranteed. ZZ is expected to remain the hardest operator.
Target expectation values are positive and O(0.2-1); individual expectations
need not converge monotonically (Z_down did not at lower chi). Do not use them
to tune weights or extrapolate chi. Monitor Gram conditioning and cancellation.

Native graph: 18-wire open path, so canonical operator MPS and exact chain
environment contraction apply. Keep independent raw-TN contraction, never
allocate dense 4^18 operators or precontract local chi^4 bra/ket objects.
Limits: 2^22 intermediate elements and 2e9 estimated FLOPs per contraction;
900-second propagation-run budget checked between states. Stop at chi128.
Save each completed state; retain failures and partial data without overwrite.

Unchanged necessary flags, chi64->128: relative full-Gram Frobenius change
<=1%, and fixed-ridge coefficient L1 change <=0.05, for each chosen operator.
They are not rigorous error bounds. Independent saved-state/hash/fit/flag audit
and the existing 33 regression tests are required. No new quantum sampling,
full-27-observable/eight-twirl result, device-model validation or 6x6 run.
Do not apply one-twirl weights to eight-twirl-averaged hardware measurements.
Keep truncation diagnostics, model bias and shot/calibration uncertainty apart.
