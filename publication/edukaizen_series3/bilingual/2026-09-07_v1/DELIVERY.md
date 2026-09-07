# Complete Nighthawk series: Nederlands / English

Published on 7 September 2026 after the user's explicit request for the full
English translation and an English/Dutch language choice.

- [English hub](https://edukaizen.nl/2d-local-quantum-advantage-en/)
- [Dutch hub](https://edukaizen.nl/2d-local-quantum-advantage/)

| Part | Dutch page ID | English page ID |
| --- | --- | --- |
| Hub | 1089 | 1121 |
| 1 | 1090 | 1122 |
| 2 | 1091 | 1123 |
| 3 | 1092 | 1124 |
| 4 | 1093 | 1125 |
| 5 | 1094 | 1126 |
| 6 | 1095 | 1127 |
| 7 | 1096 | 1128 |
| 8 | 1097 | 1129 |
| 9 | 1098 | 1130 |

Every Dutch and English page has exactly one two-link language control. The
active language is marked with `aria-current`; switching goes to the matching
part, not merely the other hub. English previous/next and reading-order links
stay within the English series. Each article container carries `lang="en"`
or `lang="nl"`. Button styling is scoped to this series, keyboard focus is
visible, and the controls can wrap on narrow screens.

The Dutch article bodies and URLs are unchanged; only the scoped language
control/style and content-language marker were inserted. The Dutch menu branch
remains under Hubbard, with no duplicate English main-menu branch. All 99 menu
items were unchanged, as were all 223 unrelated posts/pages.

## Sources and verification

- `inventory.json`: exact pre-change Dutch content and menu snapshot. All Dutch
  pages matched their historical published hashes before translation began.
- `source/en/`: complete translated article bodies, not summaries. The hub's
  reading list is generated; the Hamiltonian block is injected verbatim from
  the Dutch source to preserve every LaTeX backslash.
- `rendered/nl/` and `rendered/en/`: exact final HTML for all twenty pages.
- `payload.json`: target URLs, titles, slugs and before/after SHA-256 values.
- `translation_checks.json`: paragraph/heading/table structure, number-token
  equality with locale-aware decimal/thousands parsing, unchanged source links
  and exact LaTeX equality for all nine article pairs.
- Six offline regression tests passed in `test_nighthawk_bilingual.py`, including
  cell-by-cell table checks, exact Dutch-body recovery, reciprocal controls,
  formula equality and timing/accuracy caveats.
- `publish_receipt.json`: published IDs and server content/permalink checks.
- `public_verification.json`: all twenty URLs returned HTTP 200; each language
  switch, active language, reading-order and previous/next link was verified.
  MathJax markers were present, and no raw LaTeX shortcodes were exposed.
- `backup_receipt.json`: database backup retained outside the document root in
  a private server directory. No SQL dump was downloaded or published.

No browser screenshot or rendered-formula visual QA is claimed. Verification
covered stored content, public HTML, reciprocal links and navigation metadata.

The 7/8-second jobs, 150.819-second classical kernel, approximately 181-second
provider interval, failed TFLO holdouts, negative reconstructed probabilities,
uncertified chi64 reference and differing Google model parameters remain
explicit. No scientific result was recalculated or reclassified.

The repository remains private. No QPU job ran; LinkedIn drafts and the
Advantage List were not changed by this publication.
