# 2D Cuprate Sector-Conditioned Hardware Comparison

This report reuses existing raw bitstring counts only. No IBM Runtime, Fire Opal, or hardware job was submitted.

Postselection is a diagnostic, not mitigation proof: if few shots survive, the resulting observables have high statistical noise.

## Sector Survival

| source | profile | kept shots | total shots | kept fraction | discard fraction | unique kept | mean abs dN_up | mean abs dN_down |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| ibm | exact_sector | 7 | 128 | 0.054688 | 0.945312 | 7 | 0.000000 | 0.000000 |
| ibm | near_sector_l1_le_1 | 29 | 128 | 0.226562 | 0.773438 | 29 | 0.310345 | 0.448276 |
| ibm | near_sector_l1_le_2 | 64 | 128 | 0.500000 | 0.500000 | 64 | 0.687500 | 0.750000 |

## Site Summaries

| source | profile | total charge | total spin-z | mean abs spin-z | mean doublon | min charge | max charge |
|---|---|---:|---:|---:|---:|---:|---:|
| gaussian_u0 | free_fermion_step1 | 32.000000 | -0.000000 | 0.836350 | 0.025179 | 0.021613 | 1.000000 |
| ibm | exact_sector | 32.000000 | -0.000000 | 0.738095 | 0.059524 | 0.142857 | 1.428571 |
| ibm | near_sector_l1_le_1 | 31.862069 | -0.068966 | 0.685824 | 0.078544 | 0.206897 | 1.206897 |
| ibm | near_sector_l1_le_2 | 31.625000 | -0.187500 | 0.672743 | 0.078559 | 0.218750 | 1.234375 |
| ibm | unfiltered_raw | 31.140625 | -0.234375 | 0.650608 | 0.072700 | 0.226562 | 1.046875 |
| mps32 | reference_step1 | 32.000000 | 0.000000 | 0.840386 | 0.023625 | 0.018176 | 1.000665 |
| tdhf | mean_field_step1 | 32.000000 | -0.000000 | 0.838992 | 0.023967 | 0.021113 | 1.000001 |

## RMSE vs mps32 Step 1

| source | profile | charge RMSE | spin-z RMSE | doublon RMSE | sites |
|---|---|---:|---:|---:|---:|
| gaussian_u0 | free_fermion_step1 | 0.001181 | 0.004429 | 0.001750 | 36 |
| ibm | exact_sector | 0.178265 | 0.231115 | 0.101819 | 36 |
| ibm | near_sector_l1_le_1 | 0.132653 | 0.197027 | 0.073873 | 36 |
| ibm | near_sector_l1_le_2 | 0.140821 | 0.207018 | 0.069882 | 36 |
| ibm | unfiltered_raw | 0.137371 | 0.215794 | 0.056048 | 36 |
| tdhf | mean_field_step1 | 0.001003 | 0.001905 | 0.000682 | 36 |

## Artifacts

- site observables: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/sector_conditioned_ibm_phoenix_budgeted_s128_vs_mps/sector_conditioned_site_observables.csv`
- observable summary: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/sector_conditioned_ibm_phoenix_budgeted_s128_vs_mps/sector_conditioned_observable_summary.csv`
- RMSE: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/sector_conditioned_ibm_phoenix_budgeted_s128_vs_mps/sector_conditioned_observable_rmse.csv`
- sector summary: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/sector_conditioned_ibm_phoenix_budgeted_s128_vs_mps/sector_conditioned_sector_summary.csv`
- metadata: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/sector_conditioned_ibm_phoenix_budgeted_s128_vs_mps/sector_conditioned_metadata.json`

Interpretation boundary: sector-conditioned rows are useful to diagnose whether the correct conserved sector contains a TDHF-like signal. They are not standalone physical evidence when survival is small.
