# Fixed protocol: CZ versus X/SX residual gate noise

Question: within the previously validated residual-depolarization component,
which native gate class produces the larger loss of spin contrast at U/t=8,
T=0.4? Scope: same 3x3, 18-qubit, two-step circuit and all eight original
twirls. Preserve every native gate, physical layout and readout-X mask.
Turning off a noise channel must not remove the corresponding ideal gate.

Two new models: cz_residual_only and x_sx_residual_only. Partition the exact
saved residual-depolarization channels by instruction name. No gate-error
parameters are refitted or reassigned. Validate that channel supports are
disjoint and that their union equals the saved residual model, including
qubit ordering and full superoperators. RZ is virtual and has no saved noise.
T1/T2 and readout noise are OFF in the primary comparison. This is NOT a
comparison of the entire physical CZ error versus the entire X/SX error.

Use 8 twirls x 16 new noise trajectories = 128 per model, with the same
pershot Pauli-expectation estimator used in the component screen. Two CPU
threads; double-precision statevector, no density-matrix or MPS approximation.
Seeds: 2026091000+twirl for CZ, 2026091100+twirl for X/SX.
No new QPU jobs. Save every trajectory's 18 Z and nine onsite ZZ expectations.
Validate noise-free extraction against the frozen exact finite-circuit
reference at all eight twirls, tolerance 1e-9, and preserve 1008 CZ per circuit.

Primary summaries: raw charge, spin and doublon RMSE to the identical exact
finite-circuit reference, and g_s=(s_exact dot s_est)/(s_exact dot s_exact).
Spin is n_up-n_down; g_s=1 is the ideal contrast, not fidelity. Do not clip g_s.
Report the new CZ-only minus X/SX-only spin-RMSE and contrast differences.
128 trajectories are a bounded screening budget, not a convergence certificate.
Summarize first-8 vs all-16 per twirl as a nested, non-independent diagnostic.

2000 fixed-twirl stratified bootstrap repetitions, seed 2026091201. Resample
whole 27-vectors within each fixed twirl, independently between models.
Also apply the same analytic independent-readout moment map as a secondary
diagnostic on the SAME trajectories; its two variants share resamples.
Pointwise 95% intervals, no multiple-comparison or unknown-model-error guarantee.
Keep the previous all-residual result (128 trajectories, same estimator) as
independent historical context, not another newly generated paired sample.

Interpretation limits: the result is an aggregate circuit/noise-channel
effect, not normalized per gate and not a hardware root-cause identification.
Do not add component RMSEs or assign an additive percentage of the full
hardware error to CZ/X/SX. They occur throughout an interacting circuit.
No idle-gap relaxation, leakage, crosstalk, coherent error, drift, mitigation,
mapping optimization or circuit redesign in this segment.

Reuse the validated expectation extraction, readout map and bootstrap helpers,
without changing old code or archives. Verify raw Aer metadata and trajectories,
plus physical observables by independent two-site probability enumeration.
Save sources, protocol, gates, seeds, results, uncertainties and hashes in a new
directory. Resume only missing blocks with unchanged input/source hashes.
