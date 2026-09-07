# Phoenix readout-calibration warning

The raw main-circuit result from job `dadgm5dnj4cs73ads6ng` is valid.

The original all-0/all-1 readout circuits were transpiled independently from
the main circuit and therefore measured a different set of physical Phoenix
qubits. The derived `readout_corrected` profile is not a layout-matched
calibration and must not be used as a quantitative mitigation result.

Use the `raw` profile for this job. A corrected follow-up must calibrate the
exact physical qubits measured by the transpiled main circuit.
