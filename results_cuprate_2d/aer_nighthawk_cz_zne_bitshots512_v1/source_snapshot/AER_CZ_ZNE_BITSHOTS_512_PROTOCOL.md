# Equal-512-bitshot CZ-ZNE pilot: fixed before sampling

Same 3x3 spinful Hubbard, 18 modes, U/t=8, T=0.4, two Trotter steps,
eight original twirls and masks. Reference: same exact finite Trotter circuit.
No fresh calibration, provider calls, QPU submission or changed hardware budget.

## Arms, sharing and cost

Raw arm: 8x64=512 measured shots at factor1.
ZNE arm: 8x[37,9,18]=[296,72,144] measured shots at factors[1,2,3], total512.
Keep the previous linear intercept weights [4/3,1/3,-2/3].
Allocation [37,9,18] minimizes sum(w_i^2/n_i) over positive integer n_i
summing to64, under equal-single-shot-variance assumptions. It is based on
coefficients, not outcome data; it is not claimed optimal for actual variances.

Share the FIRST37 shots of each new raw64 block with the ZNE factor1 arm.
The last27 shots are raw-only. Prefix fixed before observing outcomes.
Only728 NEW bitshots are required:512+72+144. The two arms are correlated.
The ZNE factor1 mean MUST use296 shots, not all512 raw shots.
Use no old bitstrings (earlier512 run had overlapping RNG ranges).

Both arms have512 shots but NOT equal gate/time cost:
raw:512*1008=516096 CZ applications.
ZNE:(296+2*72+3*144)*1008=878976 CZ applications, ratio1.703125.
Common-shot reuse saves execution but does not change each arm's logical cost.
Do not call37/64 of a block runtime a measured ZNE runtime or extrapolate
these CPU times to billed QPU seconds/the prior5-second limit.

## Circuit execution

Load ORIGINAL measured QPY circuits, not generic expectation-save QPY.
Fold CZ directly in measured circuits:factor2 folds half of each ordered
CZ support; factor3 folds all. Same prior placement seeds2026300000+1000*twirl,
and require exact identity of saved fold positions. Counts1008/2016/3024.
No retranspilation, layout change, new twirls, extra one-qubit gates or clipping.
Validate identity q->classical-bit mapping and terminal18 measurements.

Use unchanged FULL calibrated channel: CZ and X/SX residual depolarization,
gate-time T1/T2, independent asymmetric readout. Every added CZ gets its full
channel. Aer samples the final measurement and readout exactly once.
After sampling only XOR the known mask; no analytic readout map, readout
inversion or postselection. Save actual binary strings and original hex memory.

New run seeds:2027100000+1000*twirl (factor1);
2027200000+1000*twirl (factor2);2027300000+1000*twirl (factor3).
Aer adds shot_index; all728 seed labels must be disjoint and outside earlier
runs. Bootstrap seed2027400000. CPU statevector double, max2 threads/shots,
truncation off, memory=True. Max runner30 minutes, no extra shots based on
significance. Preserve partial/failed runs; no automatic retry of failed blocks.

## Equations and fixed inference

Four independent strata per twirl:
A=factor1 prefix37; B=factor1 suffix27; C=factor2 nine; D=factor3 eighteen.
Average each stratum equally over the eight fixed twirls.
Raw=(37*A+27*B)/64.
Primary linear ZNE=(4*A+C-2*D)/3.
Secondary quadratic=3*A-3*C+D, same512-shot data; allocation not optimized
for that secondary. Never choose extrapolator after inspecting results.

Z=1-2*b; onsiteZZ=Zup*Zdown.
charge=1-(Zup+Zdown)/2; spin=(Zdown-Zup)/2;
doublon=(1-Zup-Zdown+ZZ)/4. Dimensionless occupations.
g=(s_exact dot s)/(s_exact dot s_exact), not fidelity.
Fit Pauli means, NOT RMSE. Primary endpoint: raw spin-RMSE minus linear-ZNE
spin-RMSE over9 sites. Charge/doublon RMSE and g are secondary.

2000 fixed-twirl bootstraps: resample COMPLETE bitstrings independently within
A,B,C,D and each twirl; rebuild both arms from the SAME draw of A.
Preserve all cross-observable and shared-shot covariance. Report pointwise95%
intervals and variance amplification. Intervals include trajectory AND sampled
measurement/readout noise, not model bias, calibration uncertainty or drift.
Quadratic, curvature, nested half/all samples and bootstrap500/1000/2000 are
diagnostics, not alternative success criteria or convergence certificates.
One pilot realization is not a calibrated repeated-experiment win rate.

The nested256-each diagnostic uses first[18,14,5,9] samples in[A,B,C,D].
Raw weights become[18/32,14/32,0,0], ZNE weights stay fixed.
Both nested arms have256 shots; this is not an independent replicate.

## Verification and interpretation

Noise-off exact27-vector for all24 circuits via freshly constructed saves.
Small measured-QPY roundtrip, deterministic and stochastic readout tests,
endianness/mask checks. Match channels to the archived model. Independently
verify ordered hex memory/counts/binary strings, occupation observables and
ZNE weights/CIs. Archive all source code, inputs, circuits, bits and hashes.

Approximate noise model still omits idle-gap, coherent/contextual errors,
crosstalk, leakage, preparation errors and drift. Gatecount is not a guaranteed
uniform effective-noise multiplier. This is selective-CZ ZNE, not all-noise-zero.
The previous34% conditional-trajectory improvement is NOT a prediction for
this equal512-bitshot experiment. Negative/unresolved results must be reported.
No hardware, equal-time or quantum-advantage claim.

Sources:
https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.AerSimulator.html
https://quantum.cloud.ibm.com/docs/en/guides/error-mitigation-and-suppression-techniques
