# Prepared next step: archived twirl1 hardware reanalysis

Status: NOT EXECUTED. Numerical prerequisites for the three central operators
now pass the predetermined exact-norm/G/b/coefficient gates and independent
audits. The raw ZZ full-Gram change still exceeds1%; retain this diagnostic.

Follow lmpf_2d/PLAN_TWIRL1_HARDWARE.md without retuning or target-driven choices.
Freeze coefficient sources before target scoring:

- Z_up, observable8: lmpf_3x3_twirl1_zup_2026-09-09_v1/chi128.json.
- Z_down, observable9: lmpf_3x3_twirl1_zdown_2026-09-09_v1/chi128.json.
- ZZ, observable22: lmpf_3x3_twirl1_zz_completed_2026-09-09_v1/chi256.json.

These paths are under results_cuprate_2d. Verify their plans, source/hash
manifests and independent audits, not just the displayed coefficient values.

Use only archived job daem7r642tqs73autong on ibm_phoenix, twirl1, native
records25/19/2; no new QPU or remote retrieval. Same64-target-shot budget:
readout64 versus ZNE/L-MPF43/7/14, plus shared128 calibration shots.

Keep subset seed2026090917, bootstrap seed2026090918,10,000 paired replicates,
the unchanged eta1 shot-aware rule, and calibration-dependent weight propagation.
No all85 primary variant, hidden clipping, number constraint, favorable seed
selection or exact-reference fit. Retain negative probabilities and unresolved
improvement intervals. The7-shot folded arm makes coverage heuristic.

Evaluate central charge, spin and doublons against the exact finite-circuit
reference only after fitting. Independently replay masks, assignment inverses,
subsets, all bootstrap draws, KKT fits and budgets. This is reused-data
robustness, not a blinded holdout or a full3x3 profile validation.

No claim of improved hardware accuracy, time advantage or6x6-go precedes
that reanalysis. Count the accumulated classical mitigation overhead separately.
