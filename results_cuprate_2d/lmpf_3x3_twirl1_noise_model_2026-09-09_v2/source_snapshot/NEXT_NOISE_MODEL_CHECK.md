# Prepared only: test the frozen noise model against individual archived arms

Status: NOT EXECUTED. Motivated by the unresolved twirl1 hardware comparison.
No new QPU, remote retrieval, new high-bond states, rate scan or target fitting.

Use the same three central twirl1 operator bundles:
Z_up chi128, Z_down chi128, onsite ZZ chi256. Verify all hashes and preserve
their original masks and actual native circuits. Compute expectation values
on the all-zero input from each stored Heisenberg operator. Physical preparation
gates are already included in those operators; do not prepare the state twice.

This needs only small MPS contractions, not a fresh state propagation. Keep a
120s process bound, one numerical thread and the existing contraction guards.
If a large state is absent, restore only via the safe archival helper.

For each operator, evaluate ideal factor1 and noisy factors1/2/3 in a fixed
order. Independently cross-check chain_expectation_zero against a raw TN
contracted with local[1,0,0,1] functionals, retaining the normalized Pauli basis.

Compare the noisy-model predictions with the corresponding readout-corrected
ARCHIVED arm means. Use all64/7/14 available target shots for this ARM-WISE
diagnostic and explicitly distinguish it from the43/7/14 matched estimator
comparison. Keep shared calibration uncertainty and two-bit correlations.

Compare the ideal TN predictions to the exact finite-circuit reference as a
separate truncation diagnostic. Do not replace the ideal operator or model
mean by that reference, and do not fit a noise rate to make agreement improve.
The exact-F00 correction is an overlap-objective constant, not permission
to rescale the saved operator expectation values.

Preserve any predicted moment outside[-1,1], negative reconstructed joint
probability, significant-looking discrepancy or broad inconclusive interval.
If the three approximate model moments do not define a valid probability
distribution, do not silently clip or renormalize before comparison.

The diagnostic is post-hoc on reused data. It may reveal model/data tension,
but cannot uniquely separate sampling, drift, coherent errors and TN bias.
Do not claim that extra shots alone remove bias or that a same-target model
fit is an independent validation. No6x6 escalation follows automatically.

Save model predictions, observed arm statistics, uncertainty, exact-ideal
differences, masks, conventions, timings and independent verification.
