---
title: "Fermi-Hubbard 2D cuprate series, part 6: 6x6 tensor baseline, IBM diagnostics, and Fire Opal Fez"
slug: "fermi-hubbard-2d-cuprate-series-part-6-6x6-tensor-ibm-fire-opal-status"
post_type: "post"
language: "en"
series: "Fermi-Hubbard 2D cuprate series"
part: 6
excerpt: "The 6x6 step reaches 72 qubits, but the current hardware result is still diagnostic: Fire Opal Fez improves strongly over IBM, while sector survival remains low."
tags:
  - quantum computing
  - Fermi-Hubbard
  - IBM Quantum
  - Fire Opal
  - tensor networks
  - MPS
---

# Fermi-Hubbard 2D cuprate series, part 6: 6x6 tensor baseline, IBM diagnostics, and Fire Opal Fez

The `6x6` step is the first 72-qubit point in this 2D series. It is the same
headline lattice size as the external Google/Willow 2D Hubbard context, but it
should not be read as the same level of physical validation.

In this series, the 6x6 run is a diagnostic scale test:

- can the 72-qubit circuit be built and submitted;
- can the same observables be compared against a tensor baseline;
- does readout correction repair the main error modes;
- does the result remain in the right particle sector;
- is Fire Opal available for the same route?

The current answer is mixed. The IBM run completed and was compared against an
MPS circuit baseline. The local baselines agree well with each other. The IBM
hardware output is much farther away. A matching 6x6 Fire Opal qelib fallback
on `ibm_fez` has now completed and has been compared against MPS chi32. The
separate `ibm_marrakesh` fallback remains a separate pending route.

## Target

The 6x6 diagnostic uses:

| item | value |
|---|---|
| lattice | `6x6` |
| sites / qubits | `36 / 72` |
| holes / doping | `4 / 0.111111` |
| expected sector | `N_up = N_down = 16` |
| parameters | `U/t = 8`, `t'/t = -0.25` |
| circuit family | `number_preserving_t_only` |
| step / dt / time | `1 / 0.1 / 0.1` |
| backend | `ibm_marrakesh` |

This is still a shallow early-time circuit. It is not a full measurement of
off-diagonal d-wave pairing, and it is not a material-level cuprate claim.

## MPS tensor baseline

Exact diagonalization is not the right reference route at this size. For this
step we use a quimb MPS simulation of the same shallow circuit family. That is
important: the MPS baseline is not a different physical experiment. It is the
same circuit family evaluated locally.

MPS convergence:

| max bond | observed max bond | elapsed s | occupation RMSE vs previous | total charge | total spin-z | mean doublon |
|---:|---:|---:|---:|---:|---:|---:|
| 16 | 16 | 6.630 | - | 32.000000 | 0.000000 | 0.021662 |
| 32 | 32 | 62.604 | 0.002741 | 32.000000 | 0.000000 | 0.023625 |

The chi16 to chi32 difference is small on the measured occupation observables.
For this short shallow step, MPS chi32 is a usable local reference.

## Local baselines versus MPS

Before interpreting hardware, the local baselines should agree with the tensor
reference. They do:

| source | reference | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---|---:|---:|---:|
| TDHF mean-field | MPS chi32 | 0.001003 | 0.001905 | 0.000682 |
| Gaussian/free | MPS chi32 | 0.001181 | 0.004429 | 0.001750 |
| MPS chi16 | MPS chi32 | 0.001034 | 0.005384 | 0.002231 |

This matters because it removes a common ambiguity. The large hardware error is
not caused by TDHF, Gaussian/free, and MPS disagreeing wildly at step 1. The
local references are close on these diagonal observables.

## IBM hardware result

The IBM hardware run completed:

| item | value |
|---|---|
| job id | `d94cogcql68s73c9clg0` |
| backend | `ibm_marrakesh` |
| shots | `1024` |
| best layout seed | `26` |
| transpiled depth | `759` |
| two-qubit gates | `2397` |
| two-qubit depth | `317` |

Summary against MPS chi32:

| route | profile | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---|---:|---:|---:|
| IBM | raw | 0.332687 | 0.733615 | 0.167283 |
| IBM | readout-corrected | 0.330085 | 0.731364 | 0.166579 |
| TDHF | mean-field | 0.001003 | 0.001905 | 0.000682 |
| Gaussian/free | free-fermion | 0.001181 | 0.004429 | 0.001750 |

Readout correction does not fix the main problem. The charge RMSE changes only
slightly, and the spin-z RMSE remains very large.

The site-level summary shows the same issue:

| profile | total charge | total spin-z | mean abs spin-z | mean doublon |
|---|---:|---:|---:|---:|
| MPS chi32 | 32.000000 | 0.000000 | 0.840386 | 0.023625 |
| IBM raw | 31.205078 | -0.591797 | 0.226237 | 0.171224 |
| IBM readout-corrected | 31.153041 | -0.455994 | 0.237755 | 0.168657 |

The total charge is not disastrous, but the spin pattern has collapsed and the
doublon estimate is much too high. This is hardware noise and sector leakage
showing up directly in the observables.

## Particle-sector diagnostic

The intended sector is part of the model. For this 6x6 run it is
`N_up = N_down = 16`.

| route | exact-sector fraction | mean abs `N_up` error | mean abs `N_down` error |
|---|---:|---:|---:|
| IBM | 0.018555 | 2.238281 | 2.238281 |
| Fire Opal qelib fallback on `ibm_fez` | 0.043945 | not reported in summary | not reported in summary |

Only about 1.9 percent of IBM shots and 4.4 percent of Fez Fire Opal shots
remain in the exact expected sector. That is the most important diagnostic
number in this chapter. At this scale, the hardware can execute the job, but
the measured distribution is not yet a clean physical distribution for the
intended particle sector.

## Fire Opal status

There are now three 6x6 Fire Opal routes in the local artifacts:

| route | action ids | status | note |
|---|---|---|---|
| abstract/native | `2331687`, `2331688` | main failed | QASM used reserved `rzz` gate name from `qelib1.inc` |
| qelib fallback on `ibm_marrakesh` | `2331689`, `2331690` | pending | left running |
| qelib fallback on `ibm_fez` | `2331691`, `2331692` | success | compared against MPS chi32 |

The qelib fallback was created to avoid the reserved-gate-name problem. Its
local QASM check passes:

| check | value |
|---|---:|
| contains `rzz` | `False` |
| contains `xx_plus_yy` | `False` |
| two-qubit count | `312` |
| two-qubit depth | `10` |
| circuit depth | `25` |

This is a much shallower Fire Opal input than the IBM-transpiled hardware
circuit. Fire Opal warned that the qelib circuit may already be
pre-processed/transpiled, so performance gains may be limited. That is the
cost of this fallback route.

## Fez Fire Opal result

The Fez Fire Opal result is much better than direct IBM, but it is still far
from the local tensor and mean-field baselines.

Summary against MPS chi32:

| route | profile | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---|---:|---:|---:|
| Fire Opal Fez | raw | 0.127246 | 0.210454 | 0.116802 |
| Fire Opal Fez | readout-corrected | 0.127916 | 0.210285 | 0.117542 |
| IBM | readout-corrected | 0.330085 | 0.731364 | 0.166579 |

The site-level summary shows the same pattern:

| profile | total charge | total spin-z | mean abs spin-z | mean doublon |
|---|---:|---:|---:|---:|
| MPS chi32 | 32.000000 | 0.000000 | 0.840386 | 0.023625 |
| Fire Opal Fez raw | 33.642578 | 0.447266 | 0.678385 | 0.098606 |
| Fire Opal Fez readout-corrected | 33.685489 | 0.456067 | 0.679056 | 0.098926 |
| IBM readout-corrected | 31.153041 | -0.455994 | 0.237755 | 0.168657 |

The Fez result recovers much more spin-z structure than direct IBM. It also
has a lower doublon error. But the total charge is high, the mean doublon is
still about four times the MPS value, and the exact-sector survival is low.

Sector-conditioned Fez rows:

| profile | kept fraction | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---:|---:|---:|---:|
| exact sector | 0.043945 | 0.114526 | 0.195952 | 0.085595 |
| near sector L1 <= 1 | 0.187500 | 0.100592 | 0.176036 | 0.086749 |
| near sector L1 <= 2 | 0.429688 | 0.102253 | 0.185340 | 0.095039 |

The near-sector rows improve the RMSE, which confirms that particle-sector
leakage is a major error source. But the exact-sector row keeps only 45 shots
out of 1024, so it is not standalone physical evidence.

## Cross-size diagnostic summary

The current step-1 hardware comparison is:

| lattice | route | reference | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---|---|---:|---:|---:|
| 3x3 | IBM readout-corrected | ED | 0.137934 | 0.221699 | 0.045795 |
| 3x3 | Fire Opal readout-corrected | ED | 0.044332 | 0.075335 | 0.028962 |
| 4x4 | IBM readout-corrected | MPS chi64 | 0.130838 | 0.190883 | 0.056986 |
| 4x4 | Fire Opal readout-corrected | MPS chi64 | 0.068299 | 0.097232 | 0.041630 |
| 6x6 | IBM readout-corrected | MPS chi32 | 0.330085 | 0.731364 | 0.166579 |
| 6x6 | Fire Opal Fez readout-corrected | MPS chi32 | 0.127916 | 0.210285 | 0.117542 |

The pattern is clear. Fire Opal improves the available 3x3 and 4x4 hardware
results. The completed 6x6 Fire Opal Fez point is much better than the direct
6x6 IBM point, especially in spin-z, but it is still not close to the local
MPS/TDHF/Gaussian baselines.

## Interpretation boundary

The 6x6 result is useful, but only as a diagnostic:

- the tensor baseline exists and is stable enough for this shallow step;
- local TDHF, Gaussian/free, and MPS agree on the diagonal observables;
- IBM hardware completed but is far from the MPS reference;
- readout correction is not enough;
- particle-sector survival is too low for a physical claim;
- Fire Opal Fez improves the 6x6 route, but its exact-sector survival remains
  too low for a physical claim.

So the next engineering target is not simply another larger run. It is a
shallower 72-qubit route with better sector protection, followed by the same
observable comparison against tensor baselines.

## Artifacts

- MPS report:
  `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/mps_shallow_t_only_steps1/cuprate_2d_mps_report.md`
- IBM summary:
  `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/ibm_hardware_steps1_shallow_t_only_best_layout/cuprate_2d_ibm_hardware_summary.md`
- observable comparison:
  `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/observable_comparison_shallow_t_only_steps1_vs_mps_hardware/cuprate_2d_observable_comparison.md`
- Fire Opal qelib fallback status:
  `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/fire_opal_qelib_fallback_status.md`
- Fire Opal qelib fallback Fez status:
  `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/fire_opal_qelib_fallback_ibm_fez_preparation_status.md`
- Fire Opal Fez observable comparison:
  `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/observable_comparison_shallow_t_only_steps1_vs_mps_qelib_fallback_ibm_fez/cuprate_2d_observable_comparison.md`
- Fire Opal Fez sector-conditioned report:
  `results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/sector_conditioned_qelib_fallback_ibm_fez_vs_mps/sector_conditioned_report.md`
