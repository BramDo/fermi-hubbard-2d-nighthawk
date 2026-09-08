# Offline chi32/64 continuation

Continue only the three central operators (8,9,22), twirl 0, ideal and actual
CZ-folded arms 1/2/3 of archived 3x3 job daem7r642tqs73autong, ibm_phoenix.
Native graph remains the verified 18-wire open path, not a 2D loop graph.
No new QPU job, no complete 27-operator/eight-twirl or 6x6 claim.

Reuse verified chi16 numeric checkpoints from the prior canonical refinement.
Compute chi32 and chi64 from the same input observables and full native gate
sequence, using the unchanged mixed-canonical propagation and fixed ridge1/56.
Do not use the reference values to fit coefficients.

Exact chain-environment overlap contracts E_ab -> sum_apb conj(A_arp) E_ab B_bsp.
An explicit two-matrix-product implementation avoids chi^4 local bra/ket
precontractions. Cross-check against independent raw-TN contraction (without
site precontraction), and dense small operators before use. Retain all scale
exponents and signs. Resource caps: 2^22 intermediate elements, 2e9 estimated
FLOPs per contraction; run cap 600 seconds checked between states.

Unchanged necessary stability flags: chi32->64 relative full-Gram Frobenius
change <=1% and fixed-ridge coefficient L1 change <=0.05, for every selected
operator. This is not an error certificate and does not waive full profile,
eight-twirl, shot/calibration or device-noise validation. Report chi16->32 as
well to see the refinement trend. Stop at chi64 in this step, preserve partial
states and failures. Independently verify hashes, fits, contractions and flags.
