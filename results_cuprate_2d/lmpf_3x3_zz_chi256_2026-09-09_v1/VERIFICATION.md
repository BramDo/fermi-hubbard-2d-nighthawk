# ZZ chi256 verification

Executed with /home/bram/.venvs/qiskit/bin/python in Ubuntu-Preview-C:
```sh
python -B lmpf_2d/verify_zz_chi256.py results_cuprate_2d/lmpf_3x3_zz_chi256_2026-09-09_v1
python -B lmpf_2d/portable_archive.py pack results_cuprate_2d/lmpf_3x3_zz_chi256_2026-09-09_v1
python -B lmpf_2d/diagnose_zz_refinement.py results_cuprate_2d/lmpf_3x3_zz_chi256_2026-09-09_v1
```

Selected actual audit output:
```text
status: HIGHER_BOND_SAVED_EVIDENCE_VERIFIED
fits_checked: 4
preserved_failures: []
maximum_gram_reconstruction_error: 1.3322676295501878e-15
maximum_optimizer_projected_gradient: 9.947554932554503e-17
maximum_ideal_expectation_reconstruction_error: 4.163336342344337e-16
largest_contracted_intermediate_elements: 262144
local_stability_flags_pass: false
full_profile_or_8_twirl_validation: false
new_qpu_seconds: 0
seconds: 8.979881456999465
```

Archive verification used the existing scripts/restore_archives.py streaming
decompressor, independently of the new packing implementation:
```text
status: PASS
selected_originals: 4
verified_objects: 4
restored: 0
already_present: 4
```
This verifies decompressed hashes and existing originals. It did not delete or
rewrite the original files. The new temporary-fixture test separately exercised
actual restoration after a generated fixture was removed, and refusal to
overwrite a mismatching fixture. All36 regression tests passed.

Actual post-hoc decomposition:
```text
relative_gram_change: 0.013098320512743785
ideal_norm_term_fraction_of_squared_gram_change: 0.9808511742954095
noisy_G_relative_change: 0.0013105259779363555
ideal_noisy_b_relative_change: 0.004988387587751139
absolute_ideal_expectation_error_128: 0.006369658678924889
absolute_ideal_expectation_error_256: 0.008275784924357016
fits_modified: false
acceptance_criteria_modified: false
```

The coefficient-L1 change 0.032186915908623104 passes 0.05, but the full-Gram
change fails 1%. The ideal expectation overshoots the exact finite-circuit
reference, and its absolute error increases. Neither result is hidden.
Alternate contraction checks saved-state computation, not the underlying
truncation error or device-model accuracy. The component decomposition is
explicitly post hoc, not a substitute acceptance test.

No new Lean proof, rigorous dynamics/error bound, full-profile/twirl validation,
noise-model validation or improved hardware/6x6 result is claimed.
