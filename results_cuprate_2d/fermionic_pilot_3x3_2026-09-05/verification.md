# Pilot execution and provenance verification

The actual provider circuit equals the frozen QPY, and all 27 physical observables match their planned Pauli mappings.
The provider confirms 512 shots and eight randomizations. Job-level execution cap: 5 seconds; billed QPU time: 3 seconds.
The execution cap is independently verified from the provider job metadata. SDK Runtime.program_run maps max_execution_time in seconds to the job-level cost field, outside the primitive input options.
The saved complete result independently reproduces the reported RMSEs. Ten source snapshots match their validation hashes.
All 37 pre-submission physics checks passed. The hardware point-estimate accuracy screen FAILED.

## Reported uncertainty diagnostics

```json
{
  "stds": {
    "shape": [
      27
    ],
    "median": 0.14426382602689833,
    "min": 0.047572028958997495,
    "max": 0.2766263208195032
  },
  "stds_noise_factors": {
    "shape": [
      27,
      3
    ],
    "median": 0.023011468101461287,
    "min": 0.012089275784316355,
    "max": 0.04118964200969363
  },
  "ensemble_stds_noise_factors": {
    "shape": [
      27,
      3
    ],
    "median": 0.02961897218922341,
    "min": 0.01809432475835786,
    "max": 0.031248450240807784
  }
}
```

Reported ZNE standard errors are retained, not replaced by 1/sqrt(shots). They can be large and do not cover every systematic extrapolation bias.
The reduction in point-estimate RMSE from factor 1 to ZNE is not claimed statistically significant: both estimates share data and their full cross-observable covariance is unavailable.
The much smaller ideal Trotter errors are separately measured against an independent Hamiltonian; they do not explain the large hardware deviations.
No additional QPU submission was made for this audit.
