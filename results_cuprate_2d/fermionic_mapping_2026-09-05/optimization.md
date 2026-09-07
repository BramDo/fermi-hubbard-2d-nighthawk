# Fermionic mapping and routing optimization

Selected network_opt3 from 6 compiled candidates; 48 valid physical paths found.
All 34 numerical checks passed.
The adaptive method preserves the old product formula exactly. The parallel network uses another second-order ordering of the same Hamiltonian.

| steps | original CZ | optimized CZ | original depth | optimized depth |
|---|---:|---:|---:|---:|
| 2 | 67793 | 15400 | 63098 | 1853 |
| 4 | 136653 | 30656 | 132008 | 3691 |
| 8 | 275834 | 61168 | 256615 | 7367 |

Optimizer-only control (2 steps): 60646 CZ, depth 59271.
Physical path ranking uses calibration errors as a heuristic, not a predicted circuit fidelity.
No extra routing SWAPs are needed. The fermionic mode order is restored after every symmetric step.
Full circuit, layout, observable, calibration, validation and candidate records are saved. No QPU job submitted.
Future settings retain 512 shots per noise factor and a maximum of 5 seconds. Gate-only duration is not billed runtime.
This is an engineering improvement, not a measured accuracy or quantum-advantage result.

Background: https://arxiv.org/abs/1711.04789 (fermionic swap networks; no resource bound from that paper is claimed for this implementation).
