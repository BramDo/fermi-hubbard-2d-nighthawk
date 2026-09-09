# Prepared only: fresh 3x3 shot and execution-budget plan

Status: NOT EXECUTED. No new hardware job is authorized.

The exact finite-count diagnostics do not reject the old central-arm model,
but they also do not validate its accuracy. The useful next step is to plan a
fresh, higher-shot 3x3 experiment with frozen analysis and a stated local budget.

First do an OFFLINE budget calculation, at most120s, without new operator
propagation or cloud submission:
- Compare64/128/256/512 shots per CZ factor, explicitly addressing the old7/14
  amplified-arm shortage. Use fixed-model covariance for planning only;
  do not promise these projected errors will be reached on hardware.
- Include contemporaneous readout calibration as a separate exposure/cost.
- Use actual saved compiled circuits and timing evidence, not a guess that
  registered QPU usage scales exactly linearly with shots.
- Preserve the distinction between raw/readout, ZNE and shot-aware L-MPF.
- For a matched-target-shot comparison, three n-shot folded arms cost3n
  target shots. A readout-only baseline also needs3n factor1 shots. Sharing
  n of them gives a data union of5n target shots, plus calibration.
  Compare QPU-time cost separately; folded shots can take longer.
- Freeze statistical endpoints, weights/rule and shot allocation before
  viewing fresh targets. Report all central charge/spin/doublon results,
  physical probability failures and paired uncertainty without clipping.
- If reusing archived Grams/weights on a fresh run, identify it explicitly
  as a transfer test. New backend calibration or different native circuits
  can invalidate old model matching; do not silently claim a current model.
- Do not pool the new run with old targets as the primary holdout result.
  Keep old analysis as training/exploratory evidence only.

Present the proposed backend, total shots, estimated QPU seconds, timing
uncertainty and stop condition to the user before any submission.
Prior5s/15s approvals are historical, not reusable. No automatic6x6 escalation.
