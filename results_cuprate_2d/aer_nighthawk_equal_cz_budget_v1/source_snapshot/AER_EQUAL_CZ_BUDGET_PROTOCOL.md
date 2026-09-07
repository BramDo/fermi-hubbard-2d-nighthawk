# Equal-CZ-budget reanalysis of archived bitshots

This is a POST-HOC, EXPLORATORY reanalysis of the already observed equal512
pilot, not an independent replicate or a new prospectively sampled experiment.
Freeze this plan before calculating the selected-subset results. No simulation,
new bitstrings, provider calls or hardware actions are allowed. Tests use only
deterministic fixtures or resampling stored numbers, never Aer.run.

## Fixed selection and estimator

Parent: results_cuprate_2d/aer_nighthawk_cz_zne_bitshots512_v2, final archive
from checkpoint00b445e. Same3x3 spinful Hubbard,18 modes,U/t=8,T=0.4,
two Trotter steps,eight fixed twirls,unchanged model and masks.

Raw arm: all64 shots per twirl at factor1,512 total.
ZNE arm: FIRST[30,5,8] shots per twirl at factors[1,2,3]:
[240,40,64],344 total. Raw and ZNE share the first240 factor1 shots.
Selected union=512+40+64=616 existing bitstrings. Remaining112 parent bitstrings
are preserved but not used for this comparison. No selection by bit value,
sector, observable quality or successful output.

Keep linear intercept weights[4/3,1/3,-2/3]. Select allocation by minimizing
16/n1+1/n2+4/n3 (the common1/9 omitted) over positive integers satisfying
n1+2*n2+3*n3=64, and verify availability. Exhaustive exact Fraction arithmetic
must give[30,5,8], objective37/30. This is an equal-single-shot-variance proxy,
not a claim of optimal allocation for actual variances or measured performance.
Do not try other allocations after seeing results.

Raw CZ cost=512*1008=516096.
ZNE CZ cost=(240+2*40+3*64)*1008=516096.
Verify equality using actual saved QPY counts, including every ordered CZ
support separately. Both arms use the same eight twirls. Other native gates
and measured qubits have344/512=43/64 of the raw count in the ZNE arm.
This does NOT establish equal wall-clock/QPU time: circuit depth, measurement
latency, reset, idle effects and per-circuit overhead have not been benchmarked.
Do not assign fractions of prior block runtimes as newly measured arm runtimes.

## Shared-shot inference and equations

Strata per twirl:
A=factor1 indices[0:30],B=factor1[30:64],C=factor2[0:5],D=factor3[0:8].
Average each over the eight fixed twirls.
raw=(30*A+34*B)/64;
linearZNE=(4*A+C-2*D)/3;
quadratic=3*A-3*C+D only as a secondary sensitivity check.
The allocation is not optimized for the quadratic estimator.

Compute Z=1-2*b and onsiteZZ=Zup*Zdown.
charge=1-(Zup+Zdown)/2; spin=(Zdown-Zup)/2;
doublon=(1-Zup-Zdown+ZZ)/4.
Dimensionless occupations; spin means n_up-n_down=2*S_z, not S_z.
g=(s_exact dot s)/(s_exact dot s_exact), not fidelity.
Fit Pauli means, not RMSE. Preserve measurement/readout noise already present.
Only decode stored mask; no new readout correction, postselection or clipping.

Primary endpoint: raw spin-RMSE minus linear-ZNE spin-RMSE across nine sites
against the frozen ideal finite-Trotter reference. Secondary:charge,doublon,g.
2000 fixed-twirl bootstraps,seed2027700000: resample whole stored bitstrings
within A,B,C,D independently for each twirl; use the SAME A draw in both arms.
Preserve cross-observable and shared-shot covariance. Do not reuse the old
bootstrap with stratum sizes[37,27,9,18].
Report pointwise95% intervals conditional on this allocation/model and dataset.
These are not selection-adjusted confirmatory intervals or an independent
replication claim. They omit extrapolation/model/calibration uncertainty.

Secondary nested HALF-CZ-budget check uses the same coefficient-only integer
optimization at32 CZ-base units: per twirl A[0:14],B[0:18],C[0:3],D[0:4].
Raw32 versus ZNE21 shots, both32 CZ-base units:14+2*3+3*4=32.
This is a sparse prefix diagnostic only, not its own significance test or
convergence certificate. Quadratic and bootstrap500/1000/2000 are diagnostics.

## Verification, archive, and limits

Verify parent hashes, original raw hex memory, counts, masks and decoded bits.
Record exact selected indices and SHA256 for all source records.
Independently compute occupations from integer bits and linear/quadratic means.
Independently reconstruct the primary gain CI from the source bootstrap draws.
Verify exact budget equality per physical ordered CZ support from QPY.
Check one-qubit/readout counts, covariance and nonphysical moments.
Save plan,code,indices,results,tests,bootstrap draws and final hash manifest
in a new folder; never modify the parent archive.

No new shots or QPU seconds. Prior observation of32% improvement at equal
shots motivated this analysis; acknowledge that dependence. A favorable result
is exploratory support within an approximate Aer model, not demonstrated
Nighthawk performance, equal-time advantage or quantum advantage.
