# Matched local Aer vs hardware: 512-shot bounded comparison

Frozen before the new noisy samples: only interacting_holdout_U8_T0.4,
18 active qubits, same 2-step finite circuit, t=1, t-prime=-0.25, U=8,
same initial state and layout as completed hardware job dae5gat1ierc738lmg10.
Use its eight submitted twirls, exactly 64 NEW Aer shots per twirl (512 total).
Do not reuse the earlier eight-shot smoke sample. No QPU or credential access.
The other nine settings and all new mitigation training are outside this run.

The physical layout, calibrated gate/readout model and zero-temperature
assumptions are unchanged from AER_NIGHTHAWK_PROTOCOL.md. No noise parameters
will be fitted to the hardware data. Missing idle relaxation, coherent noise,
crosstalk, leakage, preparation error and drift remain model limitations.
Calibration age is explicitly retained. Two CPU threads, double-precision
statevector trajectories; no density-matrix or approximate MPS truncation.
Predicted runtime is order 10-15 minutes based on the previous 8-shot timing,
not an accuracy or scaling claim. Each 64-shot block is separately archived.

Validation before noisy sampling: verify input hashes and all frozen hardware
record metadata; every native CZ must be in the saved coupling map, and all
X/SX/CZ and measurement channels covered. All eight noise-off vectors must
match the same exact 27-Pauli reference to 1e-9, with norm=1 and no leakage
outside the (4,4) particle sector. Do not recompile or remove any native gate.
Seeds: 2026090590+twirl_id, distinct from the previous smoke test.

Primary comparison is RAW Aer versus RAW hardware at this one fixed setting.
Secondary diagnostic uses the original tolerance-1 particle filter on both:
abs(Nup-4)+abs(Ndown-4)<=1; minimum 32 accepted shots overall. Never tune it.
Report raw and selected charge, spin and doublon site vectors, their RMSE to
the exact finite-circuit reference, Aer-hardware RMSE, and retention counts.
No TFLO, PEC or ZNE fit or claimed mitigation improvement in this segment.

Equations/conventions: Z=1-2*n, ZZ onsite; charge=(2-Zup-Zdown)/2,
spin=(Zdown-Zup)/2=nup-ndown (not half of this),
doublon=(1-Zup-Zdown+ZZ)/4. RMSE=sqrt(mean((estimate-reference)^2)).
Time T is dimensionless hopping*time/hbar; backend durations use their
archived SI-prefixed units via Aer. Printed MSB-first bitstrings are reversed
then XOR the original mask. A selected estimator is pooled accepted samples,
not the unweighted mean of per-twirl selected means.

Uncertainty: 2000 bootstrap repetitions, seed 2026090601, independently
resample 64 shots WITHIN each of the eight matched twirls in each dataset.
Primary inference is conditional on this fixed eight-twirl ensemble.
Retain covariance among sites/observables by resampling whole bitstrings.
Also report a sensitivity bootstrap with common resampled twirl IDs and
independent within-twirl shots; this addresses twirl variation but eight
blocks do not quantify between-job drift or model uncertainty.

Pointwise 95% intervals are descriptive, not 27 independent acceptance tests.
For raw discrepancy delta=Aer-HW, use centered bootstrap errors delta*-delta
and their 95th percentile max absolute coordinate for a simultaneous band
over 27 Pauli components. Do not use a positive RMSE confidence lower bound
as evidence of disagreement: finite-shot RMSE is positive even under equality.
An absence of resolved discrepancy is NOT proof of an equivalent noise model.

Shot-resolution diagnostic: use the first 8/16/32/64 samples PER twirl to
report 64/128/256/512-shot estimates and shot-error scales. They are nested,
not independent replicated experiments and not proof of Monte Carlo convergence.
Compare independent 32-shot halves for a separate within-simulation diagnostic.
Worst-case one-Pauli standard error at 512 shots is 1/sqrt(512)=0.0442;
the independent Aer-HW difference is bounded by sqrt(2/512)=0.0625 before PS.
Systematic error is unquantified; do not quadrature-add it to sampling error.

Save source snapshots, versions, protocol, input hashes, circuits, seeds,
raw synthetic and matched hardware data, metrics and verification separately.
No changes to existing hardware or smoke archives. If interrupted, resume
only missing blocks after checking protocol/source/input and completed hashes.
