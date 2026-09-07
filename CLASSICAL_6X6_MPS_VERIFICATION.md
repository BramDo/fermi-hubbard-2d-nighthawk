# Classical 6x6 benchmark verification, 2026-09-06

The seven bounded profiles completed. All47 archived files match their SHA-256
manifest. Eight numerical unit tests passed again together with17 hardware-pilot
tests (25 tests total): fused matrices, fermionic signs, exact2x2 state/observables,
U=0 polynomial reference, workload sizes and deadline guard.

For full6x6, T=0.4, two steps, U/t=8, t'/t=-0.25:

| Refinement | Charge RMS difference | Spin RMS difference | Doublon RMS difference | Maximum site spin difference |
|---|---:|---:|---:|---:|
| chi8 to16 | 0.0185080 | 0.0246834 | 0.00842959 | 0.0514490 |
| chi16 to32 | 0.0293691 | 0.111636 | 0.0417633 | 0.165192 |

Neither interval passes the frozen stability screen. The larger last difference
does not support extrapolating a reliable chi32 error bound. Number conservation
near1e-6 does not certify the site profiles. Chi64/128 are possible next
convergence checks, not presumed necessary or sufficient.

Chi32 kernel time is32.182951363s with1 thread and178.598521470s with3.
The maximum physical-observable difference between those runs is2.36157e-7,
checked directly from both result files. Use the faster measured run in a local
comparison. This is one execution per profile, not a timing confidence interval.
Cold worker time for1thread is36.856s; it includes imports.

The earlier chi128 estimate of tens of minutes to hours was unmeasured.
A pure cubic chi extrapolation from the faster chi32 time gives about34.3min,
but effective ranks, entanglement, BLAS behavior and implementation alter scaling.
Do not advertise that as a measured runtime or matched-accuracy lower bound.

No converged6x6 classical reference and no matched-accuracy speedup established.
The hardware pilot is a separate authorized experiment.
