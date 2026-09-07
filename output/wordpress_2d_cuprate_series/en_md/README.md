# Fermi-Hubbard 2D cuprate series - English Markdown package

This folder contains the loose English Markdown parts for the second
Edukaizen Fermi-Hubbard series.

Publication order:

1. `00_series_page.md` - series landing page
2. `01_from_1d_to_2d.md` - recap of the first 1D series and why this 2D route starts
3. `02_2d_hubbard_cuprates_google.md` - 2D Hubbard theory, cuprates, and Google/Willow context
4. `03_3x3_implementation.md` - the 3x3 validation run and implementation choices
5. `04_time_evolution_and_hardware_diagnostics.md` - ED, TDHF, Gaussian/free, IBM, and Fire Opal on 3x3
6. `05_4x4_tensor_and_hardware.md` - 4x4 IBM and Fire Opal hardware against an MPS tensor baseline
7. `06_6x6_tensor_ibm_fire_opal_status.md` - 6x6 MPS tensor baseline, IBM diagnostics, and pending Fire Opal fallback

Interpretation boundary:

The hardware output in these articles is diagnostic until it has been compared
with the local baselines and observable-comparison files. The current 2D route
is not a claim of cuprate material behavior, d-wave superconductivity, or
quantum advantage.

Current result status:

- 3x3 IBM and Fire Opal are available and compared against ED.
- 4x4 IBM and Fire Opal are available and compared against MPS chi64.
- 6x6 IBM is available and compared against MPS chi32.
- 6x6 Fire Opal qelib fallback on `ibm_fez` is available and compared against
  MPS chi32; the `ibm_marrakesh` fallback is still separate.
