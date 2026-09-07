# 3x3 full-fermion hardware pilot

Job: dadtrgjdd5gc73d7r7gg on ibm_phoenix; DONE.
18 logical qubits, one hole, N-up=N-down=4, U/t=8, t-prime/t=-0.25; two dt=0.1 steps.
ZNE factors 1/3/5, 512 shots per factor, eight twirls of 64 shots. No additional readout learning or PEC job.
Provider QPU charge time: 3 seconds; requested maximum 5 seconds.

| profile | charge RMSE | spin RMSE | doublon RMSE | total charge (target 8) |
|---|---:|---:|---:|---:|
| zne | 0.178852 | 0.476053 | 0.153609 | 8.516631 |
| factor_1 | 0.187129 | 0.504797 | 0.158411 | 8.705078 |
| factor_3 | 0.289996 | 0.761101 | 0.197507 | 8.904297 |
| factor_5 | 0.284605 | 0.813222 | 0.208393 | 9.093750 |

ZNE point-estimate screen passed: False. RMSE <= 0.05 and maximum site error <= 0.10 for each of the three observables.
Factor 1 is the unextrapolated, twirled result from the SAME job; it is not an independent no-twirling raw control.
Hardware errors above are against the exact finite-step circuit. Hamiltonian/Trotter bias is separately recorded in timestep_refinement.json and comparison.json.
Spin-z uses n-up minus n-down (twice physical S-z). No clipping, particle-sector projection, or favorable-site selection is applied.
This screen is exploratory, not statistical certification. ZNE standard errors omit possible model/systematic bias; covariance between different observables is not reconstructed.
This classically tractable pilot validates a workflow; it cannot demonstrate quantum advantage or establish 6x6 performance.
