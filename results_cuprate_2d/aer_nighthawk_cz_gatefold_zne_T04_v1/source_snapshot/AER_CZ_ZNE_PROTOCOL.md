# CZ gate-folding ZNE pilot (frozen before sampling)

Same 3x3 spinful Hubbard finite circuit: 18 modes, U/t=8, T=0.4,
two Trotter steps, eight original twirls, original masks and mapping.
Reference: ideal finite Trotter circuit; no new Trotter-error or advantage claim.

## Sample budget and controls

Reuse ONLY the corrected full-model control, 128 trajectories (8x16), from
aer_nighthawk_full_cz_half_T04_v2_disjoint_seeds. Hash-lock its final archive.
Do not reuse the earlier overlapping-seed data for statistical inference.
New groups: factor 2, factor 3, and CZ-noise-off diagnostic, each 8x16=128.
Total NEW trajectories = 384. Two CPU threads, double statevector, CPU only.
Maximum runner elapsed time 30 minutes; partial blocks preserved; no automatic
extra shots or resampling to obtain significance. No QPU/service calls.

The ZNE estimator itself uses 384 trajectories including reused factor 1.
Against the raw128 baseline it has 3x the trajectory count and 6x the CZ
applications (1+2+3). This is NOT an equal-cost or equal-shot advantage test.
The 128 CZ-off samples are a separate simulator diagnostic, not implementable
error mitigation and not part of the ZNE estimator. Do not extrapolate CPU
runtime or CZ count directly to a billed QPU duration or the old 5-second cap.

## Actual gate folding

Noise factors lambda = [1,2,3], defined by CZ counts [1008,2016,3024].
For a folded gate insert CZ CZ after the original CZ: CZ^3=CZ.
Factor 2 folds exactly half the occurrences of EACH ordered CZ support.
Counts on every support must be even; reject otherwise. Select positions
uniformly without replacement using seed 2026300000+1000*twirl.
Factor 3 folds every CZ. All original instructions and their order are retained;
no extra single-qubit gates, new twirls, remapping, or recalibration.
No transpilation after folding. Aer inserts gate noise before internal fusion;
a small exact density-matrix regression must verify folding is not canceled.
Saved QPY and per-gate fold indices make amplification auditable.

Use the unchanged FULL calibrated noise channel for every executed gate,
including extra CZ relaxation as well as CZ residual depolarization.
Unlike the preceding hypothetical study this does not reduce channel parameters.
Only CZ noise is amplified; one-qubit gate channels and readout stay fixed.
Consequently extrapolation to lambda=0 is a selective-CZ limit, NOT all-noise-zero.
The diagnostic drops CZ noise channels but retains every original ideal CZ,
all one-qubit noise, and readout; compare against it separately.

## Estimators, seeds, inference

Save 18 Z and 9 onsite ZZ expectations per noise trajectory; apply the unchanged
asymmetric readout map once analytically after the saves, in the correct mask.
Primary results include readout. These conditional expectation samples are NOT
physical bitshots; they omit final measurement-sampling variance. No readout
mitigation, postselection, clipping, or parameter fitting against ideal answers.

Simulation seeds: factor 2 = 2026400000+1000*twirl;
factor 3 = 2026500000+1000*twirl; CZ-off = 2026600000+1000*twirl.
Aer uses run_seed+shot_index. All fresh ranges, reused control ranges, and
known prior run ranges must be disjoint. Bootstrap seed 2026700000.

Primary: unweighted straight-line least-squares intercept of each Pauli moment
at lambda=0, weights [4/3,1/3,-2/3]. Weights fixed before seeing samples.
Secondary only: quadratic Richardson intercept weights [3,-3,1].
Never choose an extrapolator afterwards because it is closer to the ideal.
Fit Pauli expectations, NOT RMSE. Transform to charge, spin=nup-ndown and
doublon; evaluate RMSE across sites and spin projection g onto the ideal.
g is not fidelity. All methods retain correlations with the reused raw control.

2000 fixed-twirl bootstraps: independently resample whole trajectory vectors
within each factor and twirl; use the SAME source draws for raw, linear and
quadratic methods. Readout-on/off remain paired. Report pointwise 95% intervals
for primary spin-RMSE reduction versus raw and for each other metric.
Curvature contrast f1-2*f2+f3 and linear-vs-quadratic differences are diagnostics.
Record raw/extrapolated physical-range violations without clipping.
Nested first8/all16 per-twirl results and bootstrap500/1000/2000 check numerical
sensitivity, not full convergence or extrapolation-model accuracy.
Intervals include only conditional-trajectory Monte Carlo uncertainty, not
calibration uncertainty, fold-placement uncertainty or extrapolation bias.

## Verification and claim limits

Noise-off check against exact 27-vector for every folded circuit, tolerance1e-9.
Verify original instruction trace is an ordered subsequence with exactly the
recorded CZ-pair additions; per-support CZ counts scale exactly.
Full model channels/readout must match the saved control; CZ-off changes no
non-CZ channel. Validate small-circuit ideal identities and noisy folded response
against exact density-matrix / depolarizing-channel formulas.
Independently reconstruct physical observables and primary gain from raw Zs.
Hash all code, inputs, circuits, trajectories, analyses, diagnostic tests.

Model omits idle-gap relaxation, coherent/contextual noise, crosstalk, leakage,
preparation errors and drift. Hardware mismatch remains a separate issue.
Report negative or statistically unresolved results honestly. This is a local
ZNE screen, not proven hardware mitigation, beyond-classical dynamics, or a
reproduction of an unspecified paper's protocol.

Official guidance: https://quantum.cloud.ibm.com/docs/en/guides/error-mitigation-and-suppression-techniques
Aer expectation saves: https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.library.save_expectation_value.html
Pinned RNG rule: https://github.com/Qiskit/qiskit-aer/blob/0.17.2/src/simulators/circuit_executor.hpp#L823-L834

Pre-run regression note: explicit Kraus(Kraus-derived pure depolarizing p=.1)
with forced fusion threshold1 caused Aer 0.17.2 heevx/eigensystem_hermitian
failure in the 2q fixture. The underlying cause is not claimed resolved.
The exact density-matrix depolarizing folding test passes. The independent
statevector/Kraus test instead uses two local amplitude-damping channels,
whose folded occupation is analytically (1-.1)^6. With fusion actually applied,
4096 trajectories give Z=-.0644572 versus exact -.062882. This tests the same
folding/noise-insertion mechanism without the failing degenerate fixture.
No production noise model or folded production result is changed to avoid it.
If the production channel run triggers an error, stop and preserve the failure.
