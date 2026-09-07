# Full 6x6 chi=64 continuation

One CPU-only run. Concurrent local work: timing is not isolated.
Same finite-step fermionic circuit as the existing 6x6 hardware job.

Kernel time: 150.819180 s; cold worker: 156.905497 s.
Total number: 31.999999197; error from 32: -8.02965e-07.
Log retained norm: -1.5252795 (not a fidelity/error bound).

| Comparison | RMS charge | RMS spin | RMS doublon | Max charge | Max spin | Max doublon |
|---|---:|---:|---:|---:|---:|---:|
| chi64_minus_chi32_threads1 | 0.0147349729 | 0.0553820231 | 0.0206365946 | 0.0340240014 | 0.0769678693 | 0.0379487076 |
| chi64_minus_chi32_threads3 | 0.0147349863 | 0.0553820408 | 0.0206365975 | 0.0340241271 | 0.0769678454 | 0.0379487496 |

All signed site differences and thread-sensitivity comparisons are in summary.json.

A single chi=32 -> 64 difference is not a certified convergence/error bound.
This does not establish that chi=64 is exact or chi=128 is required/sufficient.
No shot noise applies; truncation, roundoff/thread dependence and discretization remain distinct.
No quantum-advantage or matched-accuracy claim follows from these times alone.
