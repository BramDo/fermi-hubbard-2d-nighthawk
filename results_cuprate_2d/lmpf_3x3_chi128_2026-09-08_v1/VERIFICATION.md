# Chi128 verification

Executed in the existing WSL Qiskit environment:

```sh
python -B lmpf_2d/verify_higher_bond.py results_cuprate_2d/lmpf_3x3_chi128_2026-09-08_v1
```

Actual audit output (selected fields):

```text
status: HIGHER_BOND_SAVED_EVIDENCE_VERIFIED
fits_checked: 12
preserved_failures: []
maximum_gram_reconstruction_error: 2.3314683517128287e-15
maximum_optimizer_projected_gradient: 3.7009241157792694e-16
maximum_ideal_expectation_reconstruction_error: 7.771561172376096e-16
largest_contracted_intermediate_elements: 65536
local_stability_flags_pass: false
full_profile_or_8_twirl_validation: false
new_qpu_seconds: 0
seconds: 6.516225149003731
```

The 33-test suite passed before propagation; `tests.txt` retains its output.
The independent verifier hashes every saved manifest entry and the captured
numerical source, reconstructs all Gram entries with raw-TN contraction and
changed tensor ordering, and checks PSD, fit stationarity, normalization,
projection residuals and threshold classification without the production flag
function. Chi64 baseline copies were additionally hash-matched to the parent.

Z_up and Z_down pass both fixed local flags; ZZ fails both. No execution or
fit failure occurred, but the combined convergence test did not pass.
Floating-point agreement does not bound the underlying MPS truncation error.
This is not a Lean proof, a Hamiltonian-dynamics error certificate, full-profile
hardware validation, device-noise validation, or a 6x6 mitigation result.
