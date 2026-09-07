# Report design and provenance notes

Audience: technical; main value is converting observables and validating
comparability. Surface: canonical HTML fallback after an accepted MCP call
without an inspectable Codex viewer. No publication.

Required structure mapping: title; technical summary; scope/definitions
moved before numerical evidence to prevent misunderstanding; values table;
profile RMS chart/table with adjacent interpretation; convergence and
validation; algebraic methodology; limitations; next steps and open question
merged because both ask for a matched model and accuracy protocol.

Chart contract: category comparison, grouped native bar chart. Six cases
times three observables =18 reviewed rows, not a time series. It compares
residuals against each case's OWN reference, expressly not true error or
matched performance. Keep all four selected Google configurations to avoid
choosing only the best layer count. Zero baseline. Three categorical series
(charge, spin, doublons) with visible legend and category labels; reader's
shared palette. Full-width report block, dense exact values in the adjacent
table; no second chart necessary. Source datasets retain model, reference,
filling, site count, time, source path and other numerical context.

The 14-row full raw/readout/mitigated lookup remains in the executed
notebook and comparison.json. The report focuses on six mitigated rows.
No fabricated confidence intervals: primitive covariance unavailable.
No numerical initial-state metadata silently repaired. Raw HDF payloads
are read with a restricted NumPy-only unpickler and bounded storage checks.

QA: canonical artifact validator passed, HTML packaging and structural
verification passed. No compatible Chromium headless-shell; visual QA,
legend appearance and clipping at laptop/mobile widths remain unchecked.
The semantic HTML tables preserve all report values if enhanced charts
cannot start. Numeric verification is independent of rendering.
