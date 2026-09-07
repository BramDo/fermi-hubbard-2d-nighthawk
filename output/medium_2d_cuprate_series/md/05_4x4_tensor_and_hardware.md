# Fermi-Hubbard 2D cuprate series, part 5: 4x4 hardware and tensor baselines

Originally published at:
https://edukaizen.nl/fermi-hubbard-2d-cuprate-series-part-5-4x4-hardware-and-tensor-baselines/

Part 5 of 6 in the Fermi-Hubbard 2D cuprate series.
Series page: https://edukaizen.nl/fermi-hubbard-2d-cuprate-series/

The next run after 3x3 is `4x4`. This is where the validation strategy has to
change. Exact diagonalization is no longer the comfortable general reference,
so the route needs tensor baselines.

The 4x4 run in this series uses:

- lattice: `4x4`
- sites: `16`
- qubits: `32`
- holes: `2`
- expected sector: `N_up = N_down = 7`
- circuit family: `number_preserving_t_only`
- step: `1`
- `dt = 0.1`
- hardware backend: `ibm_marrakesh`

This is still a shallow early-time run. It is not the final interacting
cuprate problem. Its purpose is to test whether the 2D stack still works when
the lattice is large enough that exact ED is no longer the default reference.

## Circuit depth

The 4x4 dry-run gave:

| route | logical depth | transpiled IBM depth | two-qubit gates | two-qubit depth |
|---|---:|---:|---:|---:|
| 3x3 IBM step 1 reference | 8 | 167 | 159 | 52 |
| 4x4 IBM step 1 | 8 | 199 | 341 | 65 |
| 4x4 Fire Opal abstract input | 8 | not hardware-compiled | 64 logical | 5 logical |

The two-qubit gate count roughly doubles relative to 3x3, but the two-qubit
depth grows much less because the circuit has parallel structure.

That is encouraging, but not enough. On current hardware, two-qubit depth and
sector survival remain the limiting issues.

## MPS circuit baseline

For 4x4, this route adds a quimb MPS circuit baseline for the same shallow
circuit family. This is important: it is an apples-to-apples circuit baseline
for the hardware output. It is not a full Hamiltonian TDVP solution for all
cuprate physics, but it is the right reference for the shallow circuit that was
actually run.

The MPS convergence ladder was:

| max bond | observed max bond | elapsed s | occupation RMSE vs previous | total charge | total spin-z | mean doublon |
|---:|---:|---:|---:|---:|---:|---:|
| 32 | 32 | 13.497 | None | 14.000000 | 0.000000 | 0.020073 |
| 64 | 64 | 49.455 | 0.000202737 | 14.000000 | 0.000000 | 0.020170 |

The `chi32 -> chi64` occupation RMSE is about `2.0e-4`. For this short shallow
step, the MPS run is numerically stable enough to serve as the local
reference.

Local baselines against MPS chi64:

| source | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---:|---:|---:|
| TDHF | 0.000660 | 0.002011 | 0.000995 |
| Gaussian/free | 0.000955 | 0.000917 | 0.000088 |

At this very early step, both TDHF and Gaussian/free are close to the shallow
circuit baseline on the diagonal observables. That should not be overread. It
means this run is still an early-time circuit diagnostic, not a late-time
strong-correlation benchmark.

## IBM hardware result

The 4x4 IBM job was:

- job id: `d93v9a6vtlqs73ftm6mg`
- backend: `ibm_marrakesh`
- status: `DONE`
- shots: `1024`
- main transpiled depth: `199`
- two-qubit count: `341`
- two-qubit depth: `65`

Hardware summary:

| profile | total charge | total spin-z | mean abs spin-z | mean doublon |
|---|---:|---:|---:|---:|
| raw | 13.766602 | -0.340820 | 0.650818 | 0.072632 |
| readout-corrected | 13.881690 | -0.242608 | 0.685372 | 0.064137 |
| MPS chi64 | 14.000000 | 0.000000 | 0.833332 | 0.020170 |

RMSE against MPS chi64:

| source | profile | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---|---:|---:|---:|
| IBM | raw | 0.119908 | 0.218926 | 0.059685 |
| IBM | readout-corrected | 0.130838 | 0.190883 | 0.056986 |
| IBM | exact-sector | 0.097011 | 0.123450 | 0.044959 |

The exact-sector result is better than raw and readout-corrected, but it is
still not close enough to treat as a clean physical result.

## Sector survival

Particle-sector survival is the central diagnostic:

| profile | kept shots | total shots | kept fraction |
|---|---:|---:|---:|
| exact sector `N_up = N_down = 7` | 133 | 1024 | 0.129883 |
| near sector L1 <= 1 | 462 | 1024 | 0.451172 |
| near sector L1 <= 2 | 762 | 1024 | 0.744141 |

Only about 13 percent of shots remain in the exact expected sector. Near-sector
analysis shows that many errors are close to the right sector, but not all the
way there.

That is a useful hardware diagnostic. It is also the reason this result should
not be presented as a final 4x4 physics result.

## Fire Opal result

The 4x4 abstract/native Fire Opal route was not the final usable path. The
working route was a qelib retry for the same shallow `number_preserving_t_only`
step. That gives a cleaner comparison because IBM, Fire Opal, TDHF,
Gaussian/free, and MPS are all evaluated on the same diagonal observables.

RMSE against MPS chi64:

| source | profile | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---|---:|---:|---:|
| IBM | raw | 0.119908 | 0.218926 | 0.059685 |
| IBM | readout-corrected | 0.130838 | 0.190883 | 0.056986 |
| IBM | exact-sector | 0.097011 | 0.123450 | 0.044959 |
| Fire Opal | raw | 0.065163 | 0.104742 | 0.045752 |
| Fire Opal | readout-corrected | 0.068299 | 0.097232 | 0.041630 |
| Fire Opal | exact-sector | 0.026794 | 0.021459 | 0.013010 |

The Fire Opal result is clearly closer to the MPS baseline than direct IBM. The
exact-sector Fire Opal row is especially strong, but it must still be read with
the survival fraction in mind.

Sector survival:

| route | exact-sector kept shots | total shots | kept fraction |
|---|---:|---:|---:|
| IBM | 133 | 1024 | 0.129883 |
| Fire Opal | 267 | 1053 | 0.253561 |

Fire Opal roughly doubles the exact-sector survival for this 4x4 case and
reduces the RMSE substantially. That is an engineering improvement, not a
superconductivity claim.

## Conclusion

The 4x4 run is useful because it exposes the next bottleneck.

Direct IBM hardware can run the circuit, but noise and sector leakage dominate.
The MPS baseline is stable enough for this short shallow step. Fire Opal is
much cleaner than direct IBM, especially after exact-sector conditioning, but
the result is still diagnostic because the survival fraction is only about
25 percent.

So the next improvement is not simply a larger lattice. The next improvement is
a better route:

- shallower circuits;
- better fermion routing;
- stronger layout selection;
- better readout and sector mitigation;
- a larger MPS convergence ladder, for example `chi = 32, 64, 128`;
- separate 6x6 analysis only with a matching tensor or operator baseline.

Only after that does a larger 2D dry-run become physically meaningful.
