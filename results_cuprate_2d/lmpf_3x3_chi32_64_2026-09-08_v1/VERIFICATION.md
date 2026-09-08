# Chi32/64 verification

Executed in the existing WSL Qiskit environment:

```sh
python -B lmpf_2d/verify_higher_bond.py results_cuprate_2d/lmpf_3x3_chi32_64_2026-09-08_v1
```

Selected actual output:

```text
status: HIGHER_BOND_SAVED_EVIDENCE_VERIFIED
fits_checked: 18
preserved_failures: []
maximum_gram_reconstruction_error: 2.3314683517128287e-15
maximum_optimizer_projected_gradient: 3.7009241157792694e-16
maximum_ideal_expectation_reconstruction_error: 7.771561172376096e-16
largest_contracted_intermediate_elements: 16384
local_stability_flags_pass: false
full_profile_or_8_twirl_validation: false
new_qpu_seconds: 0
```

The 33-test suite passed before the run. Independent raw-TN contraction checks
the explicit matrix-product chain environment; source snapshots, parent and
result hashes preserve provenance. Fit normalization, PSD, stationarity,
projection residual and the stability flags were reconstructed independently.

Software/evidence validation passed; physical convergence did not pass the
predeclared local flags. `preserved_failures: []` refers to execution/fit
failures, not to acceptance of the numerical convergence. No Lean proof,
device-noise validation, full-profile validation or 6x6 result is claimed.
