# IBM Phoenix 6x6: raw versus Floquet-style XY4/twirling

Status: completed 2026-09-04.

## Frozen comparison

- backend: `ibm_phoenix` (Nighthawk r2)
- target: 6x6 / 72 qubits, step 1, `dt=0.1`
- shots per job: 128
- main ISA instruction SHA-256: `04ce79265b36fdf43237072ee0093d39aa9f50354128cab275cadf4eb138847e`
- main measurement-map SHA-256: `f1157e328d04018410a01e672d20ca50e924b0f312ac1d3acc9548a0c8795dd6`
- transpiled depth / two-qubit count / two-qubit depth: `249 / 777 / 89`

The two jobs used the same main ISA circuit and physical measurement mapping.

| route | job id | QPU charge time | DD | gate twirling |
|---|---|---:|---|---|
| direct | `dadgm5dnj4cs73ads6ng` | 3 s | off | off |
| Floquet-style suppression | `dadhca3dd5gc73d7b8vg` | 3 s | XY4 | 4 x 32 shots |

## RMSE versus MPS chi32

| route/profile | charge | spin-z | doublon |
|---|---:|---:|---:|
| direct raw | 0.137371 | 0.215794 | 0.056048 |
| XY4/twirling raw | 0.225324 | 0.333308 | 0.114316 |
| XY4/twirling readout-corrected | 0.223382 | 0.318909 | 0.117927 |

The original direct job's readout calibration was not layout-matched, so its
`readout_corrected` profile is excluded. Its raw profile remains valid.

## Particle-sector survival

| route | exact-sector shots | exact-sector fraction |
|---|---:|---:|
| direct | 7 / 128 | 0.054688 |
| XY4/twirling | 1 / 128 | 0.007812 |

## Conclusion

For this single low-shot pilot, XY4 plus gate twirling did not improve any of
the three RMSE metrics and reduced exact-sector survival. The direct raw route
remains the better Phoenix result. This is not a general verdict on XY4 or
twirling: 128 shots and one calibration window are insufficient for that.

Fire Opal 12.1 supported-device discovery did not include `ibm_phoenix`, so no
Fire Opal validation or execution was attempted on this backend. The
validate-only workflow used zero quantum seconds.

Total Phoenix charge time across the two jobs was 6 QPU seconds. At the IBM
Pay-As-You-Go list price of USD 1.60 per second, that corresponds to about
USD 9.60 before any account-specific pricing differences.
