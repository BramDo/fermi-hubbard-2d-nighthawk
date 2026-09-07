# 4x4 Fire Opal qelib retry summary

Submitted on 2026-07-04 for the existing 4x4 validation run:

- case: `results_cuprate_2d/validation_ladder_steps1/cuprate_4x4_holes2_steps1`
- route: Fire Opal qelib retry, `number_preserving_t_only`, step 1, `dt = 0.1`
- backend: `ibm_marrakesh`
- main action: `2331685`, status `SUCCESS`
- readout action: `2331686`, status `SUCCESS`
- note: the earlier abstract/native retry produced action `2331683` for main but it ended as `FAILURE`; its readout action was `2331684`.

Fire Opal emitted a warning that the qelib circuit may already have undergone preprocessing/transpilation, so Q-CTRL performance gains may be limited. The qelib route is therefore a diagnostic fallback, not the preferred abstract input.

## Site summary

| source | profile | total charge | total spin-z | mean abs spin-z | mean doublon |
|---|---|---:|---:|---:|---:|
| MPS chi64 | reference | 14.000000 | 0.000000 | 0.833332 | 0.020170 |
| IBM | raw | 13.766602 | -0.340820 | 0.650818 | 0.072632 |
| IBM | readout corrected | 13.881690 | -0.242608 | 0.685372 | 0.064137 |
| Fire Opal qelib | raw | 14.268756 | -0.061728 | 0.753977 | 0.055318 |
| Fire Opal qelib | readout corrected | 14.103323 | 0.104219 | 0.764103 | 0.046188 |
| Fire Opal qelib | exact sector | 14.000000 | -0.000000 | 0.827715 | 0.019195 |

## RMSE vs MPS chi64

| source | profile | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---|---:|---:|---:|
| IBM | raw | 0.119908 | 0.218926 | 0.059685 |
| IBM | readout corrected | 0.130838 | 0.190883 | 0.056986 |
| IBM | exact sector | 0.097011 | 0.123450 | 0.044959 |
| Fire Opal qelib | raw | 0.065163 | 0.104742 | 0.045752 |
| Fire Opal qelib | readout corrected | 0.068299 | 0.097232 | 0.041630 |
| Fire Opal qelib | exact sector | 0.026794 | 0.021459 | 0.013010 |

## Sector survival

| source | profile | kept shots | total shots | kept fraction |
|---|---|---:|---:|---:|
| IBM | exact sector | 133 | 1024 | 0.129883 |
| IBM | near sector L1 <= 1 | 462 | 1024 | 0.451172 |
| IBM | near sector L1 <= 2 | 762 | 1024 | 0.744141 |
| Fire Opal qelib | exact sector | 267 | 1053 | 0.253561 |
| Fire Opal qelib | near sector L1 <= 1 | 654 | 1053 | 0.621083 |
| Fire Opal qelib | near sector L1 <= 2 | 895 | 1053 | 0.849953 |

## Artifacts

- Fire Opal summary: `cuprate_2d_fire_opal_summary.md`
- Fire Opal raw results: `fire_opal_raw_results.json`
- Observable comparison: `../observable_comparison_shallow_t_only_steps1_vs_mps_fire_opal_qelib_retry/cuprate_2d_observable_comparison.md`
- Sector-conditioned comparison: `../sector_conditioned_fire_opal_qelib_retry_steps1_vs_mps/sector_conditioned_report.md`

Interpretation boundary: these are diagonal-observable hardware diagnostics for the shallow 4x4 circuit family. The exact-sector Fire Opal row is much closer to the MPS circuit baseline than direct IBM, but it is postselected and keeps only about 25 percent of shots; it is not a standalone physical claim.
