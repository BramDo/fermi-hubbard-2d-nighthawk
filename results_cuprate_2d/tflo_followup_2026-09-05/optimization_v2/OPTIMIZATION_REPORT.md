# One-qubit cleanup: local validation only

CZ count and per-wire CZ ordering, readout mask and measurement mapping are preserved.
Optimization was performed BEFORE parameter binding; calibration and interacting inputs keep one fixed structure per twirl.

| Twirl | X before | X after | X+SX before | X+SX after | Depth before | Depth after |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 2256 | 550 | 3938 | 2228 | 906 | 630 |
| 1 | 2213 | 575 | 3895 | 2253 | 887 | 630 |
| 2 | 2163 | 566 | 3845 | 2244 | 896 | 631 |
| 3 | 2284 | 588 | 3966 | 2266 | 896 | 630 |
| 4 | 2088 | 555 | 3770 | 2233 | 896 | 634 |
| 5 | 2167 | 568 | 3849 | 2246 | 898 | 623 |
| 6 | 2240 | 546 | 3922 | 2224 | 898 | 637 |
| 7 | 2270 | 557 | 3952 | 2235 | 904 | 632 |

138 checks passed; maximum full-statevector phase-aligned distance 2.944e-14.
QPY round-trip equality verified. No new QPU run and no claim of improved hardware fidelity.
The old measurement data belong to the OLD circuits; the separate reanalysis cannot test these new circuits.

Optimizer reference: https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.transpiler.passes.Optimize1qGatesDecomposition
