# Independent hardware verification

Executed from provider BitArrays using separate inverse matrices and an OLS solve.

```json
{
  "status": "PASS_INDEPENDENT_HARDWARE_AUDIT",
  "job_id": "daem7r642tqs73autong",
  "actual_qpu_seconds": 3,
  "cap_seconds": 5,
  "provider_pub_bitarrays_and_QPY_verified": 26,
  "new_hardware_shots": 808,
  "total_executed_CZ_applications": 967680,
  "independent_inverse_matrix_and_OLS_error": 4.440892098500626e-16,
  "independent_physical_error": 3.3306690738754696e-16,
  "primary_spin_gain_interval_independently_reproduced": [
    0.039739924619583145,
    0.1408108625987948
  ],
  "relative_spin_rmse_reduction": 0.27753519438609714,
  "relative_spin_reduction_hybrid95": [
    0.10701431039449934,
    0.38407775102796543
  ],
  "maximum_noise_off_error": 2.2648549702353193e-14,
  "noise_off_checks": 24,
  "prior_archive_files_verified": 95,
  "tests": 74,
  "resubmission_performed": false,
  "scope": "Single 3x3 hardware pilot, matched shot budgets but not gate/time budgets."
}
```
