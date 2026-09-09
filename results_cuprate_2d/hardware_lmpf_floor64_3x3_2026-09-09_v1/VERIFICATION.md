# Verification: fresh 3x3 floor64 hardware analysis

## Scope and result

**Numerical/retrieval audit passed; physical mitigation is not globally validated.**
Executed on 2026-09-09 using WSL Ubuntu-Preview-C and the existing
`/home/bram/.venvs/qiskit/bin/python`, CPU only.

The live retrieval confirmed DONE for job `dago39b9k43c73adleeg`.
All 20 provider circuits, shot counts and metadata matched the frozen plan;
all 3,072 width-18 shots were archived. IBM confirmed a 5-second maximum
and reported complete usage of 3 QPU seconds.

The analysis verified the frozen hardware and analysis manifests. The
calibration-only point weights were saved before fresh target counts were
decoded. No exact target values were used to fit coefficients.

## Executed primary checks

`analysis/tests.txt` records **5 tests passed** in 0.020 seconds:
calibration broadcasting, floor penalty, independent inverse/KKT, rejection
of incomplete/wrong-role data, and preservation of sixteen target PUB strata.

The fresh analysis completed with:
`FRESH_FLOOR64_HARDWARE_ANALYZED`.

## Level 5: independently executed reproduction

Command (offline, from the project root):

```text
/home/bram/.venvs/qiskit/bin/python -B lmpf_2d/verify_floor_hardware_analysis.py results_cuprate_2d/hardware_lmpf_floor64_3x3_2026-09-09_v1/analysis
```

Actual output, also saved in `analysis/verification/verification.json`:

```json
{
  "status": "FRESH_FLOOR64_ASSIGNMENT_KKT_BOOTSTRAP_AUDIT_PASSED",
  "job_id": "dago39b9k43c73adleeg",
  "methods_checked": 5,
  "bootstrap_replicates_replayed": 10000,
  "maximum_differences": {
    "paulis": 5.995204332975845e-15,
    "physical": 3.552713678800501e-15,
    "physical_fixed_calibration": 2.1094237467877974e-15,
    "floor_weights": 4.08006961549745e-15,
    "original_weights": 3.730349362740526e-14,
    "low_floor_weights": 4.135580766728708e-15
  },
  "same_shot_comparison_verified": true,
  "calibration_only_fit_verified": true,
  "no_clipping_verified": true,
  "seconds": 1.2387178509961814
}
```

The verifier uses a separate full 4x4 assignment-matrix inverse, direct KKT
linear systems and separate bit-order extraction. It regenerates all shared
calibration draws and sixteen-PUB multinomials, checks all five estimators,
paired intervals, point joint probabilities, coefficient flags, shot budgets,
pre/post calibration and the exact reference against the frozen hardware plan.

## Preserved limitations and failed physical outcomes

- The reference is exact for the finite circuit, not a continuous-time proof.
- Original and floor64 L-MPF point doublon probabilities are negative and uncut.
- Floor64 has no all-three-observable improvement over any baseline.
- Sampling intervals omit systematic noise/model/TN/drift/correlated-readout bias.
- Marginal positive paired bounds are not simultaneous statistical guarantees.
- Coefficient stability alone is not a hardware noise-model validation.
- Equal shots do not mean equal QPU time; 3 charged seconds are not end-to-end.
- No 6x6 approval, new submission or quantum advantage claim follows.

All original submission records and unrelated symbolic work are preserved.

