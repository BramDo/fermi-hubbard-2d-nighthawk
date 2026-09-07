# Nighthawk project operating rules

- Read README.md and theory/RESULTS_AND_CLAIMS.md before changing a claim.
- This is a copied working tree with fresh Git history. Preserve archived
  source files and failed/control results; do not rewrite historical evidence.
- Creating, cloning or working in this repo does NOT authorize QPU use.
  Require fresh explicit user permission for each new job and exact budget.
  Historical approvals and attempt receipts are not reusable authorization.
- Default to offline tests. Do not instantiate cloud services merely to check
  imports; do not run scripts named submit or once as smoke tests.
- Keep job IDs, backend, mitigation arm, reference and timing scope together.
- The ~20x result is a ratio of local classical kernel time to registered QPU
  usage, not matched-accuracy or end-to-end advantage. chi64 is uncertified.
- TFLO target estimates remain unvalidated; failed holdouts and negative
  reconstructed probabilities are material findings, not removable clutter.
- Use scripts/restore_archives.py for heavy artifacts; never overwrite a
  mismatching restored file. Keep all archive parts below 10 MB.
- Do not publish articles, alter Edukaizen navigation, enable Pages, or change
  repository visibility without an explicit request. Draft status is default.
