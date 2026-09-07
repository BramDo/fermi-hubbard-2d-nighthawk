# Student Advantage List registration — 2026-09-07

The user explicitly requested adding this project to the Edukaizen and GitHub
student advantage lists. It is now the seventh entry:
`fermi-hubbard-2d-nighthawk-72q`.

- [Edukaizen](https://edukaizen.nl/pro-student-quantum-advantage-list/#fermi-hubbard-2d-nighthawk-72q)
- [Public GitHub entry](https://github.com/BramDo/pro-student-quantum-advantage-list/blob/main/entries/fermi-hubbard-2d-nighthawk-72q.json)
- [GitHub Pages](https://bramdo.github.io/pro-student-quantum-advantage-list/#fermi-hubbard-2d-nighthawk-72q)

Public list commit: `86fb5086154e295275dd2a2839f78de71e133462`.
Classification: **Local execution-metric ratio; accuracy unvalidated**
(`local_execution_metric`). No existing entry was reclassified.

The primary ratio is 150.81918013700124 / 7 = 21.54559716242875 (circa 20x).
The separate 8-second DD/TFLO job supports 18.85x and is not added to the paired
job. The approximately 181-second provider running-to-finished interval, failed
TFLO holdouts, negative reconstructed probabilities, unvalidated observables
and uncertified chi64 reference all remain visible. There is no end-to-end or
matched-accuracy advantage claim, and no chi128 result is invented.

## Verification

- 13 local regression tests passed; deterministic build/check passed.
- All seven entries passed the complete JSON schema with format checks.
- Kernel, cold-worker, charged-QPU and provider-interval numbers matched the
  original local evidence files. The six old WordPress entry sections remained
  byte-for-byte intact. The old hardcoded introductory count was made dynamic.
- WordPress page 451 was updated in place after a private server database backup;
  232 other posts/pages and all 99 menu items were preserved. The grouped Hubbard
  navigation was not changed.
- Public Edukaizen HTTP 200, unique new section/table link, ratio, mitigation and
  access caveats verified.
- Public GitHub source and deployed JSON feed exactly matched the local entry;
  GitHub Pages returned HTTP 200. Both validation and Pages deployment passed for
  the public commit above. See `github_verification.json`.

The public contribution follows the list's detailed-public-report admission
route. The complete research repository remains PRIVATE, confirmed live after
publication. Only the list entry, public reports and access notice were exposed;
no raw research archive, credentials or SQL backup was published. No QPU job ran.

`before.html` and the hash-guarded `payload.json` preserve the page change;
`preflight.json`, `publish_receipt.json`, `public_verification.json` and
`github_verification.json` record the checks. `public_entry_snapshot.json` freezes
the new public entry in this private research archive as well.
