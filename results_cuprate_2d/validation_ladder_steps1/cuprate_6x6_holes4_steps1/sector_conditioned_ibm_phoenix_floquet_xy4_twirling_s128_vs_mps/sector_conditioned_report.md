# 2D Cuprate Sector-Conditioned Hardware Comparison

This report reuses existing raw bitstring counts only. No IBM Runtime, Fire Opal, or hardware job was submitted.

Postselection is a diagnostic, not mitigation proof: if few shots survive, the resulting observables have high statistical noise.

## Sector Survival

| source | profile | kept shots | total shots | kept fraction | discard fraction | unique kept | mean abs dN_up | mean abs dN_down |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| ibm | exact_sector | 1 | 128 | 0.007812 | 0.992188 | 1 | 0.000000 | 0.000000 |
| ibm | near_sector_l1_le_1 | 11 | 128 | 0.085938 | 0.914062 | 11 | 0.545455 | 0.363636 |
| ibm | near_sector_l1_le_2 | 35 | 128 | 0.273438 | 0.726562 | 35 | 0.685714 | 0.971429 |

## Site Summaries

| source | profile | total charge | total spin-z | mean abs spin-z | mean doublon | min charge | max charge |
|---|---|---:|---:|---:|---:|---:|---:|
| gaussian_u0 | free_fermion_step1 | 32.000000 | -0.000000 | 0.836350 | 0.025179 | 0.021613 | 1.000000 |
| ibm | exact_sector | 32.000000 | 0.000000 | 0.833333 | 0.027778 | 0.000000 | 2.000000 |
| ibm | near_sector_l1_le_1 | 32.363636 | -0.363636 | 0.651515 | 0.093434 | 0.363636 | 1.181818 |
| ibm | near_sector_l1_le_2 | 32.400000 | -0.514286 | 0.611111 | 0.102381 | 0.485714 | 1.142857 |
| ibm | unfiltered_raw | 33.414062 | -0.554688 | 0.562717 | 0.128255 | 0.546875 | 1.250000 |
| mps32 | reference_step1 | 32.000000 | 0.000000 | 0.840386 | 0.023625 | 0.018176 | 1.000665 |
| tdhf | mean_field_step1 | 32.000000 | -0.000000 | 0.838992 | 0.023967 | 0.021113 | 1.000001 |

## RMSE vs mps32 Step 1

| source | profile | charge RMSE | spin-z RMSE | doublon RMSE | sites |
|---|---|---:|---:|---:|---:|
| gaussian_u0 | free_fermion_step1 | 0.001181 | 0.004429 | 0.001750 | 36 |
| ibm | exact_sector | 0.405832 | 0.512758 | 0.164162 | 36 |
| ibm | near_sector_l1_le_1 | 0.238089 | 0.299523 | 0.107018 | 36 |
| ibm | near_sector_l1_le_2 | 0.223606 | 0.307443 | 0.091443 | 36 |
| ibm | unfiltered_raw | 0.225324 | 0.333308 | 0.114316 | 36 |
| tdhf | mean_field_step1 | 0.001003 | 0.001905 | 0.000682 | 36 |

## Artifacts

- site observables: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/sector_conditioned_ibm_phoenix_floquet_xy4_twirling_s128_vs_mps/sector_conditioned_site_observables.csv`
- observable summary: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/sector_conditioned_ibm_phoenix_floquet_xy4_twirling_s128_vs_mps/sector_conditioned_observable_summary.csv`
- RMSE: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/sector_conditioned_ibm_phoenix_floquet_xy4_twirling_s128_vs_mps/sector_conditioned_observable_rmse.csv`
- sector summary: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/sector_conditioned_ibm_phoenix_floquet_xy4_twirling_s128_vs_mps/sector_conditioned_sector_summary.csv`
- metadata: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/sector_conditioned_ibm_phoenix_floquet_xy4_twirling_s128_vs_mps/sector_conditioned_metadata.json`

Interpretation boundary: sector-conditioned rows are useful to diagnose whether the correct conserved sector contains a TDHF-like signal. They are not standalone physical evidence when survival is small.
