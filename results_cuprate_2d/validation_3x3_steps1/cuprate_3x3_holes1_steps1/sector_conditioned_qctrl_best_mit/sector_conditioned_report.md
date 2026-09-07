# 2D Cuprate Sector-Conditioned Hardware Comparison

This report reuses existing raw bitstring counts only. No IBM Runtime, Fire Opal, or hardware job was submitted.

Postselection is a diagnostic, not mitigation proof: if few shots survive, the resulting observables have high statistical noise.

## Sector Survival

| source | profile | kept shots | total shots | kept fraction | discard fraction | unique kept | mean abs dN_up | mean abs dN_down |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| ibm | exact_sector | 84 | 1024 | 0.082031 | 0.917969 | 83 | 0.000000 | 0.000000 |
| ibm | near_sector_l1_le_1 | 309 | 1024 | 0.301758 | 0.698242 | 307 | 0.368932 | 0.359223 |
| ibm | near_sector_l1_le_2 | 611 | 1024 | 0.596680 | 0.403320 | 608 | 0.667758 | 0.689034 |
| fire_opal | exact_sector | 97 | 1027 | 0.094450 | 0.905550 | 76 | 0.000000 | 0.000000 |
| fire_opal | near_sector_l1_le_1 | 371 | 1027 | 0.361246 | 0.638754 | 314 | 0.347709 | 0.390836 |
| fire_opal | near_sector_l1_le_2 | 679 | 1027 | 0.661149 | 0.338851 | 602 | 0.650957 | 0.659794 |

## Site Summaries

| source | profile | total charge | total spin-z | mean abs spin-z | mean doublon | min charge | max charge |
|---|---|---:|---:|---:|---:|---:|---:|
| fire_opal | exact_sector | 8.000000 | -0.000000 | 0.508591 | 0.137457 | 0.432990 | 1.144330 |
| fire_opal | near_sector_l1_le_1 | 8.048518 | 0.053908 | 0.449835 | 0.150943 | 0.547170 | 1.212938 |
| fire_opal | near_sector_l1_le_2 | 8.108984 | 0.144330 | 0.428735 | 0.155785 | 0.583211 | 1.206186 |
| fire_opal | unfiltered_raw | 8.493671 | 0.295034 | 0.388294 | 0.180569 | 0.672833 | 1.221032 |
| gaussian_u0 | free_fermion_step1 | 8.000000 | 0.000000 | 0.853300 | 0.017061 | 0.041738 | 0.999302 |
| ibm | exact_sector | 8.000000 | 0.000000 | 0.089947 | 0.215608 | 0.321429 | 1.166667 |
| ibm | near_sector_l1_le_1 | 7.841424 | -0.061489 | 0.086659 | 0.201007 | 0.320388 | 1.106796 |
| ibm | near_sector_l1_le_2 | 7.716858 | 0.034370 | 0.076923 | 0.197309 | 0.338789 | 1.116203 |
| ibm | unfiltered_raw | 7.234375 | 0.117188 | 0.076606 | 0.171332 | 0.333008 | 1.055664 |
| tdhf | mean_field_step1 | 8.000000 | 0.000000 | 0.855090 | 0.016260 | 0.040736 | 0.999552 |

## RMSE vs TDHF Step 1

| source | profile | charge RMSE | spin-z RMSE | doublon RMSE | sites |
|---|---|---:|---:|---:|---:|
| fire_opal | exact_sector | 0.215436 | 0.389879 | 0.145849 | 9 |
| fire_opal | near_sector_l1_le_1 | 0.231558 | 0.440298 | 0.152355 | 9 |
| fire_opal | near_sector_l1_le_2 | 0.238425 | 0.461932 | 0.156446 | 9 |
| fire_opal | unfiltered_raw | 0.248265 | 0.501067 | 0.177270 | 9 |
| gaussian_u0 | free_fermion_step1 | 0.000373 | 0.001896 | 0.000849 | 9 |
| ibm | exact_sector | 0.396836 | 0.901273 | 0.221417 | 9 |
| ibm | near_sector_l1_le_1 | 0.379172 | 0.870705 | 0.202347 | 9 |
| ibm | near_sector_l1_le_2 | 0.363854 | 0.861285 | 0.196266 | 9 |
| ibm | unfiltered_raw | 0.370618 | 0.864282 | 0.168553 | 9 |

## Artifacts

- site observables: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/sector_conditioned_qctrl_best_mit/sector_conditioned_site_observables.csv`
- observable summary: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/sector_conditioned_qctrl_best_mit/sector_conditioned_observable_summary.csv`
- RMSE: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/sector_conditioned_qctrl_best_mit/sector_conditioned_observable_rmse.csv`
- sector summary: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/sector_conditioned_qctrl_best_mit/sector_conditioned_sector_summary.csv`
- metadata: `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/sector_conditioned_qctrl_best_mit/sector_conditioned_metadata.json`

Interpretation boundary: sector-conditioned rows are useful to diagnose whether the correct conserved sector contains a TDHF-like signal. They are not standalone physical evidence when survival is small.
