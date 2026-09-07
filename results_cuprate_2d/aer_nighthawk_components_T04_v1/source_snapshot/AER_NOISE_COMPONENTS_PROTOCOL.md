# Component screening inside the existing Nighthawk Aer model

Scope fixed before the component samples: existing U/t=8, T=0.4, 3x3,
18 active wires, eight original twirls, two Trotter steps, 1008 CZ per circuit.
No new hardware, no retuning to hardware, no idle/crosstalk/coherent model yet.

Question: which terms already present in the approximate model can produce
loss of spin contrast? This is a model ablation, NOT identification of the
real hardware error mechanism or a mitigation effectiveness experiment.

Models: ideal; readout-only (exact moments of the saved Aer readout channels);
residual depolarization only; gate-time T1/T2 relaxation only. For the last
two use 8 twirls x 16 independent noise trajectories = 128 per model, with
two CPU threads and double-precision statevectors. This is a bounded screen,
not a fully converged estimate. Reuse the previous full-model 512 sampled
bitstrings as context, clearly labeling its different estimator/sample size.

Do NOT call gate_error=True, thermal_relaxation=False and interpret that as
the residual gate component: that would reassign the full reported gate
infidelity to depolarization. Instead preserve the original decomposition.
For d=2^k and R the gate-time relaxation channel, reconstruct residual
depolarization D_p from F_full and F_R using
p=d*(F_R-F_full)/(d*F_R-1). The original channel is D_p.compose(R).
Check every reconstructed superoperator against the original model to 1e-12.
When R already reaches the reported error floor, p=0. No noise is refitted.

Readout: for each qubit p01=P(measure1|true0), p10=P(measure0|true1),
a=1-p01-p10, b=p10-p01. In the mask-corrected frame b_m=(-1)^mask*b,
Z_out=a*Z+b_m. For onsite i,j:
ZZ_out=a_i*a_j*ZZ+a_i*b_mj*Z_i+a_j*b_mi*Z_j+b_mi*b_mj.
This follows the independent readout channels in the original Aer model.
Readout-only moments are exact in that model, not sampled hardware data.

Keep final readout-X gates in each native circuit. Remove terminal measurements
only for the expectation-value estimator, append 18 Z and 9 onsite ZZ saves,
and save every trajectory's 27 moments (pershot=True), not just an average.
Undo the saved readout mask. Also apply the analytic readout transformation
to the SAME trajectories as an extra paired diagnostic, requiring no new run.
Validate the expectation-value extraction against the existing exact reference
for all eight noiseless circuits and on a small noisy-channel test.

Primary summaries: raw spin, charge and doublon RMSE to the identical exact
finite-circuit reference, and spin-contrast projection
g_s=sum(s_exact*s_est)/sum(s_exact^2), where s=nup-ndown.
Ideal g_s=1. This is NOT fidelity and must not be clipped to [0,1].
Report no postselection or TFLO/PEC/ZNE results in this component screen.
Do not add component RMSEs or claim that separately removed channels have
additive effects; the channels act throughout an interacting circuit.

Uncertainty: fixed-eight-twirl stratified bootstrap, independently resample
the 16 WHOLE trajectory vectors within each twirl, 2000 repetitions, seed
2026090901. Readout-added and no-readout estimates use the same resamples.
Component-to-component draws are independent. Report pointwise 95% intervals,
not a multiple-comparison guarantee. Show first-8 vs all-16 trajectories per
twirl as a nested resolution diagnostic, NOT independent convergence proof.
Gate component seeds 2026090700+twirl; relaxation seeds 2026090800+twirl.
Saved expectation values remove measurement sampling noise, not noise-trajectory
Monte Carlo uncertainty or model uncertainty. Label this explicitly.

Expected before the run: readout-only can be evaluated exactly and should be
small given percent-level readout errors. Many accumulated gate-noise events
and relaxation can each reduce spin amplitude; their ordering is not assumed.
No negative or greater-than-one projection will be discarded or tuned away.

Store the original-model decomposition, sources, masks, seeds, all trajectory
moments, Aer metadata, calibration, checks and hashes in a new folder.
Preserve every earlier hardware, full-model and smoke result.

Official API reference:
https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.library.save_expectation_value.html
