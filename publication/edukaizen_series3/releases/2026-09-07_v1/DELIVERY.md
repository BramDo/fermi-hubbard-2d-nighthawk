# Published: 2D Local Quantum Advantage

Date: 2026-09-07. Site: https://edukaizen.nl.
User authorization: publish these articles on their own page named
"2D local quantum advantage". Only the public article package was uploaded;
the private research archive and database backup were not published.

[Open the hub](https://edukaizen.nl/2d-local-quantum-advantage/).

Subsequent authorized navigation change on the same date: all three Hubbard
series were grouped under one top-level **Hubbard** item. See the separate
[navigation receipt](../../navigation/2026-09-07_hubbard_group/DELIVERY.md).
The preservation checks below describe the initial publication stage.

| Part | Page ID | Parent page | Menu ID | Subject |
| --- | --- | --- | --- | --- |
| Hub | 1089 | 0 | 1109 | 2D Local Quantum Advantage |
| 1 | 1090 | 1089 | 1110 | Local goal and budget |
| 2 | 1091 | 1089 | 1111 | Full fermion model |
| 3 | 1092 | 1089 | 1112 | Mapping and circuit depth |
| 4 | 1093 | 1089 | 1113 | Pilots, shots and noise |
| 5 | 1094 | 1089 | 1114 | Readout, ZNE, PEC and TFLO |
| 6 | 1095 | 1089 | 1115 | Charge, spin and doublons |
| 7 | 1096 | 1089 | 1116 | Meaning of the circa 20x ratio |
| 8 | 1097 | 1089 | 1117 | Google and Bonsai comparison |
| 9 | 1098 | 1089 | 1118 | Next validation step |

## Evidence

- `publish_package.json`: exact public HTML, source and HTML SHA-256 values,
  intended titles, slugs and URLs; source commit 6151dcaaa146e0280a02233ab4eccf2499a6825f.
- `publish_receipt.json`: all ten pages published; exact stored content and
  URLs checked; 223 unrelated pages/posts and all 88 existing menu items preserved.
- `public_verification.json`: HTTP 200 for all ten URLs, hub links to all nine
  articles, title and navigation markers, no draft notices or old draft-hub links,
  no unprocessed LaTeX shortcodes, MathJax script markers on formula pages,
  homepage menu link, unchanged existing menu fields and relative order.
- `backup_receipt.json`: database exported before publication to the private
  server directory, outside the website document root. The SQL file was neither
  downloaded nor committed. `transport.json` records its directory.
- Chrome visual QA was unavailable: the browser binding failed twice, although
  the installed extension was detected. No screenshot/rendered-math or responsive
  layout verification is claimed. Public HTML/links and WP content were checked.

## Ordinal menu check and read-only recovery

The initial publisher completed all page and menu writes, then its strict
position check stopped. The only difference was Advantage List (menu ID 452):
its displayed ordinal changed from 88 to 98 after adding ten new items. Its
stored menu order is 1000, so it remains the separate final top-level item.
No old title, URL, parent or relative order changed.

`partial_receipt.json` preserves that intermediate state. The separate
`scripts/verify_edukaizen_series3.php` checked all old content signatures,
new page ownership and exact HTML, unique slug/parent identities, all menu
relationships and the single expected ordinal shift. It made no WordPress
content or menu edits; only the completion receipt and cache flush followed.
There was no blind resubmission, duplicated page or full-site restoration.

## Interpretation and access

The title names the local benchmark project, not a certified universal advantage.
The approximately 20x ratio remains explicitly classical kernel time divided by
registered QPU usage, not end-to-end or matched-accuracy advantage. Chi64
nonconvergence and failed TFLO holdouts remain in the public articles.

The original Markdown and draft HTML/manifest are preserved separately. These
release files, not the old draft manifest, identify the published state.
The GitHub repository was verified PRIVATE after publication. No QPU job was
submitted and no new hardware authorization was inferred.
