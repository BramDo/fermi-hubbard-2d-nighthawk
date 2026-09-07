# 6x6 Fire Opal qelib Fallback ibm_fez Submission Status

Prepared on 2026-07-04 after a live backend queue check showed `ibm_fez` had a
shorter queue than `ibm_marrakesh`.

Submitted on 2026-07-04 after explicit user request: `submit fez`.

## Existing Marrakesh Route

- output dir: `fire_opal_shallow_t_only_qelib_fallback`
- backend: `ibm_marrakesh`
- main action id: `2331689`
- readout action id: `2331690`
- latest known main status: `PENDING`
- latest known readout status: `PENDING`

This route should be left running. The Fez route below uses separate output
directories and does not overwrite the Marrakesh submission artifacts.

## Live Backend Queue Snapshot

- `ibm_fez`: 156 qubits, operational `True`, pending jobs `11`
- `ibm_marrakesh`: 156 qubits, operational `True`, pending jobs `25`

## Fez Dry Run

- dry-run output: `fire_opal_shallow_t_only_qelib_fallback_ibm_fez_dryrun`
- backend: `ibm_fez`
- qasm basis: `qelib`
- qasm optimization level: 1
- submit requested: `False`
- main/readout shots: 1024 / 4096
- main QASM parse ok: `True`
- contains `rzz`: `False`
- contains `xx_plus_yy`: `False`
- main two-qubit count/depth/depth: 312 / 10 / 25
- main QASM characters: 24258

## Fez Submission

- output dir: `fire_opal_shallow_t_only_qelib_fallback_ibm_fez`
- backend: `ibm_fez`
- main action id: `2331691`
- readout action id: `2331692`
- submitted groups: `main`, `readout`
- shots main/readout: 1024 / 4096
- first poll main status: `PENDING`
- first poll readout status: `PENDING`
- Fire Opal metadata created_at main/readout: `2026-07-04 12:20:14` / `2026-07-04 12:20:21`

## Fez Retrieval

Retrieved on 2026-07-04 after the user reported Fez was ready.

- latest main status: `SUCCESS`
- latest readout status: `SUCCESS`
- main updated_at: `2026-07-04 12:26:30`
- readout updated_at: `2026-07-04 12:25:53`
- summary: `fire_opal_shallow_t_only_qelib_fallback_ibm_fez/cuprate_2d_fire_opal_summary.md`
- raw payloads: `fire_opal_shallow_t_only_qelib_fallback_ibm_fez/fire_opal_result_payloads.json`
- raw counts: `fire_opal_shallow_t_only_qelib_fallback_ibm_fez/fire_opal_raw_results.json`
- site observables: `fire_opal_shallow_t_only_qelib_fallback_ibm_fez/cuprate_2d_fire_opal_site_observables.csv`
- bond observables: `fire_opal_shallow_t_only_qelib_fallback_ibm_fez/cuprate_2d_fire_opal_bond_observables.csv`
- plot: `fire_opal_shallow_t_only_qelib_fallback_ibm_fez/cuprate_2d_fire_opal_readout_corrected_observables.png`

Fire Opal emitted a warning that the qelib circuit may already have undergone
pre-processing/transpilation, so performance gains may be limited. This is
expected for the qelib fallback and is why the result remains a diagnostic
route, not the ideal abstract Fire Opal input.

## Fez Observable Snapshot

| profile | total charge | total spin-z | mean abs spin-z | mean doublon |
|---|---:|---:|---:|---:|
| Fire Opal raw | 33.642578 | 0.447266 | 0.678385 | 0.098606 |
| Fire Opal readout corrected | 33.685489 | 0.456067 | 0.679056 | 0.098926 |
| MPS chi32 reference | 32.000000 | 0.000000 | 0.840386 | 0.023625 |

RMSE versus MPS chi32:

| profile | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---:|---:|---:|
| Fire Opal raw | 0.127246 | 0.210454 | 0.116802 |
| Fire Opal readout corrected | 0.127916 | 0.210285 | 0.117542 |
| IBM readout corrected | 0.330085 | 0.731364 | 0.166579 |

Sector-conditioned RMSE versus MPS chi32:

| profile | kept fraction | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---:|---:|---:|---:|
| Fire Opal exact sector | 0.043945 | 0.114526 | 0.195952 | 0.085595 |
| Fire Opal near sector L1 <= 1 | 0.187500 | 0.100592 | 0.176036 | 0.086749 |
| Fire Opal near sector L1 <= 2 | 0.429688 | 0.102253 | 0.185340 | 0.095039 |

The Fez Fire Opal result is much better than direct IBM, especially for
spin-z, but it is still far above the local MPS/TDHF/Gaussian baselines. The
exact-sector survival is only 45/1024 shots, so sector-conditioned rows are
diagnostic and statistically thin.

## Fez Comparison Artifacts

- observable comparison: `observable_comparison_shallow_t_only_steps1_vs_mps_qelib_fallback_ibm_fez/cuprate_2d_observable_comparison.md`
- sector-conditioned report: `sector_conditioned_qelib_fallback_ibm_fez_vs_mps/sector_conditioned_report.md`

Retrieve wrapper:

- `scripts/retrieve_cuprate_2d_6x6_fire_opal_shallow_t_only_qelib_fallback_ibm_fez_wsl.ps1`

## Separate Fez Scripts

Dry-run:

- `scripts/run_cuprate_2d_6x6_fire_opal_shallow_t_only_qelib_fallback_ibm_fez_dryrun_wsl.ps1`

Submit script used after explicit submit decision:

- `scripts/submit_cuprate_2d_6x6_fire_opal_shallow_t_only_qelib_fallback_ibm_fez_wsl.ps1`

Retrieve after submitted Fire Opal actions exist:

- `scripts/retrieve_cuprate_2d_6x6_fire_opal_shallow_t_only_qelib_fallback_ibm_fez_wsl.ps1`

Compare after both Fez actions succeed:

- `scripts/compare_cuprate_2d_6x6_shallow_t_only_qelib_fallback_ibm_fez_vs_mps_wsl.ps1`

Claim boundary: this is a prepared duplicate backend route for diagonal
observables only. Hardware output remains diagnostic until compared against the
local MPS/TDHF/Gaussian baselines and sector diagnostics.
