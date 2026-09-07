# 2D Cuprate Sector-Conditioned Hardware Comparison

This report reuses existing raw bitstring counts only. No IBM Runtime, Fire Opal, or hardware job was submitted.

Postselection is a diagnostic, not mitigation proof: if few shots survive, the resulting observables have high statistical noise.

## Sector Survival

| source | profile | kept shots | total shots | kept fraction | discard fraction | unique kept | mean abs dN_up | mean abs dN_down |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| ibm | exact_sector | 19 | 1024 | 0.018555 | 0.981445 | 19 | 0.000000 | 0.000000 |
| ibm | near_sector_l1_le_1 | 98 | 1024 | 0.095703 | 0.904297 | 98 | 0.367347 | 0.438776 |
| ibm | near_sector_l1_le_2 | 232 | 1024 | 0.226562 | 0.773438 | 232 | 0.681034 | 0.814655 |
| fire_opal | exact_sector | 45 | 1024 | 0.043945 | 0.956055 | 45 | 0.000000 | 0.000000 |
| fire_opal | near_sector_l1_le_1 | 192 | 1024 | 0.187500 | 0.812500 | 191 | 0.421875 | 0.343750 |
| fire_opal | near_sector_l1_le_2 | 440 | 1024 | 0.429688 | 0.570312 | 439 | 0.788636 | 0.672727 |

## Site Summaries

| source | profile | total charge | total spin-z | mean abs spin-z | mean doublon | min charge | max charge |
|---|---|---:|---:|---:|---:|---:|---:|
| fire_opal | exact_sector | 32.000000 | 0.000000 | 0.700000 | 0.069136 | 0.111111 | 1.222222 |
| fire_opal | near_sector_l1_le_1 | 32.223958 | 0.098958 | 0.708478 | 0.071036 | 0.145833 | 1.255208 |
| fire_opal | near_sector_l1_le_2 | 32.470455 | 0.206818 | 0.700189 | 0.077336 | 0.150000 | 1.327273 |
| fire_opal | unfiltered_raw | 33.642578 | 0.447266 | 0.678385 | 0.098606 | 0.226562 | 1.383789 |
| gaussian_u0 | free_fermion_step1 | 32.000000 | -0.000000 | 0.836350 | 0.025179 | 0.021613 | 1.000000 |
| ibm | exact_sector | 32.000000 | -0.000000 | 0.271930 | 0.172515 | 0.421053 | 1.210526 |
| ibm | near_sector_l1_le_1 | 32.071429 | -0.112245 | 0.240646 | 0.174887 | 0.438776 | 1.336735 |
| ibm | near_sector_l1_le_2 | 31.840517 | -0.064655 | 0.236231 | 0.177083 | 0.439655 | 1.306034 |
| ibm | unfiltered_raw | 31.205078 | -0.591797 | 0.226237 | 0.171224 | 0.457031 | 1.335938 |
| mps32 | reference_step1 | 32.000000 | 0.000000 | 0.840386 | 0.023625 | 0.018176 | 1.000665 |
| tdhf | mean_field_step1 | 32.000000 | -0.000000 | 0.838992 | 0.023967 | 0.021113 | 1.000001 |

## RMSE vs mps32 Step 1

| source | profile | charge RMSE | spin-z RMSE | doublon RMSE | sites |
|---|---|---:|---:|---:|---:|
| fire_opal | exact_sector | 0.114526 | 0.195952 | 0.085595 | 36 |
| fire_opal | near_sector_l1_le_1 | 0.100592 | 0.176036 | 0.086749 | 36 |
| fire_opal | near_sector_l1_le_2 | 0.102253 | 0.185340 | 0.095039 | 36 |
| fire_opal | unfiltered_raw | 0.127246 | 0.210454 | 0.116802 | 36 |
| gaussian_u0 | free_fermion_step1 | 0.001181 | 0.004429 | 0.001750 | 36 |
| ibm | exact_sector | 0.359391 | 0.739286 | 0.197667 | 36 |
| ibm | near_sector_l1_le_1 | 0.339295 | 0.735845 | 0.175217 | 36 |
| ibm | near_sector_l1_le_2 | 0.331805 | 0.733503 | 0.173987 | 36 |
| ibm | unfiltered_raw | 0.332687 | 0.733615 | 0.167283 | 36 |
| tdhf | mean_field_step1 | 0.001003 | 0.001905 | 0.000682 | 36 |

## Artifacts

- site observables: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/sector_conditioned_qelib_fallback_ibm_fez_vs_mps/sector_conditioned_site_observables.csv`
- observable summary: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/sector_conditioned_qelib_fallback_ibm_fez_vs_mps/sector_conditioned_observable_summary.csv`
- RMSE: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/sector_conditioned_qelib_fallback_ibm_fez_vs_mps/sector_conditioned_observable_rmse.csv`
- sector summary: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/sector_conditioned_qelib_fallback_ibm_fez_vs_mps/sector_conditioned_sector_summary.csv`
- metadata: `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/sector_conditioned_qelib_fallback_ibm_fez_vs_mps/sector_conditioned_metadata.json`

Interpretation boundary: sector-conditioned rows are useful to diagnose whether the correct conserved sector contains a TDHF-like signal. They are not standalone physical evidence when survival is small.
