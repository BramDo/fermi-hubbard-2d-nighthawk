# TFLO 3x3 verification

Passed: 682 archive checks and 98 exact-physics checks.

Full local unit-test output: unit_tests.txt; exit code 0.

Largest FLO/full-statevector difference: 1.784e-13.
Native template: 1008 CZ; depth 549.

All 80 planned setting/twirl records retain their compiled structure after binding. The two-spin sector filter, TFLO fit, raw Sampler archive, hierarchical bootstrap and held-out-reference leakage tests ran locally. Synthetic readout errors in tests are not a calibrated Phoenix noise model. No hardware improvement is claimed.

Budget: 512 shots per setting, 5120 including calibration and holdouts. No QPU job submitted; not established to fit the existing 5-second cap.

Symmetry averaging remains disabled because nontrivial physical symmetries are not exact on the finite-step reference grid. MESR, GPR and DD are not implemented in this prototype. The fixed ridge prior is not the paper's learned regularizer.
