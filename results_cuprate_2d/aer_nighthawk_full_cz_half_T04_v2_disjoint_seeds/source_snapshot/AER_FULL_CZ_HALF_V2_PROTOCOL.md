# Full calibrated model versus halved residual CZ depolarization

Scope fixed before new samples: U/t=8, T=0.4, same 3x3, 18-qubit,
two-Trotter-step circuit, all eight original twirls, 1008 CZ per circuit.
Two new runs with disjoint per-shot RNG seed ranges, 8 x 16 = 128 noise trajectories each. Same
expectation-value estimator, masks, readout map, CPU limit and sample budget.
No QPU, no fresh calibration, no circuit changes, no fitted parameters.

Control: the original complete CALIBRATED AER MODEL (gate depolarization,
gate-time T1/T2 and independent asymmetric readout). Intervention: replace
only residual CZ D_p by D_(p/2), leaving CZ relaxation R and every non-CZ
channel identical. Keep composition D_p.compose(R), as in the original model.
The reported total CZ gate infidelity is NOT halved because relaxation remains.
No X/SX noise, T1/T2 value, duration or readout error is reduced.

Validate scale=1 against all original saved full-model gate superoperators;
validate scale=0 against the CZ relaxation channel; verify non-CZ channels
and readout matrices unchanged, and half-p exactly p/2. Preserve every gate.
For all eight noise-free circuits, require max Pauli error <1e-9 against
the frozen finite-circuit reference. Keep normalization and physical marginals.

Save 18 Z and 9 onsite ZZ expectations for EVERY noise trajectory (pershot).
Terminal measurements are replaced by those saves, so the readout channel is
applied once, analytically, afterwards in the correct readout-X mask frame.
Noise-model JSONs also contain the readout channels for reproducibility;
the absence of measurement instructions means they do not act on saved
premeasurement expectation values. Test that explicitly on a small circuit.
The PRIMARY comparison includes this unchanged analytic readout map.
The pre-readout values are a secondary diagnostic, not the primary result.

Primary metrics: charge, spin, doublon RMSE across nine sites against the
same ideal finite-circuit reference; spin contrast g=(s_exact dot s)/(s_exact
dot s_exact), where s=nup-ndown. g is not fidelity and is not clipped.
Benefit means control RMSE minus half-CZ RMSE; contrast benefit means
half-CZ g minus control g. Positive values indicate improvement.

2000 stratified bootstrap repetitions within the fixed eight twirls, seed
2026092201. Resample whole 27-vectors; datasets have independent trajectories.
Before/after-readout variants of the SAME dataset retain paired resampling.
Pointwise 95% intervals, not a simultaneous significance guarantee. Report
first-8 versus all-16 per twirl as a nested diagnostic, not convergence proof.
Run seeds: 2026100000+1000*twirl for control, 2026200000+1000*twirl for half-CZ.
Aer 0.17.2 uses run seed + shot index; verify that all 16 ranges of 16 are disjoint.

Heuristic expectation, NOT a fitted target: from the preceding isolated
CZ effect (~0.13 spin-RMSE), halving it in the full noisy circuit might give
an improvement of order 0.02-0.10; no effect or an unresolved difference
must also be reported honestly. Expected runtime several minutes per model
on two CPU threads, with a hard 30-minute process limit and saved blocks.

The older full-Aer 512-bitstring result is historical context only; its twirl
seeds overlap across shots, so its independent-bootstrap CIs are not valid;
the new control and intervention use the SAME 128-trajectory estimator.
No shot postselection, ZNE, PEC, mitigation fitting or hardware-advantage claim.
Hypothetically reducing a channel is not an implemented error-mitigation scheme.

Full here does NOT mean all real hardware errors: idle-gap relaxation,
crosstalk, leakage, coherent/contextual noise, preparation errors and drift
are still missing from the existing model. The earlier hardware mismatch
remains. Save all sources, assumptions, inputs, channels, trajectories,
tests and hashes without altering any earlier archive.

Pre-run compatibility finding: AerJSONEncoder serializes complex matrix
entries as [real,imag] pairs; QuantumError.from_dict does not restore that
extra axis itself. Decode only Kraus/unitary matrix parameters on a copied
dictionary before verifying the saved model. Preserve the original JSON.
Test nonzero imaginary entries, not only the real relaxation matrices.
This was found during validation before any new noisy sampling; the earlier
simulations used in-memory channels and are not changed by this reader fix.

## v2 correction, frozen before resampling

v1 has been preserved without overwriting any samples or analyses. Its 19.2%
spin-error reduction is provisional: seeds base+twirl overlap across Aer shots.
This affects uncertainty assumptions in the previous 512-shot, component and
CZ-vs-X/SX screens too, not the actual QPU bitstrings or hardware shot count.
The channel/circuit algebra checks remain useful. Do not claim that all old
point estimates are wrong, nor that overlapping RNG streams wholly explain
the old/new control discrepancy. Different twirls are not identical circuits.

Official pinned source: https://github.com/Qiskit/qiskit-aer/blob/0.17.2/src/simulators/circuit_executor.hpp
Lines 823-834 initialize each shot RNG using circuit seed plus shot index,
except shot zero uses the initial engine. A local 1q Kraus-noise regression
reproduces a shifted trajectory sequence with adjacent run seeds.
This follow-up repeats the SAME physics question and same 128/model budget
with disjoint seeds; it does not optimize or select seeds for a good result.
Only one v2 batch is planned. No further resampling based on significance.
