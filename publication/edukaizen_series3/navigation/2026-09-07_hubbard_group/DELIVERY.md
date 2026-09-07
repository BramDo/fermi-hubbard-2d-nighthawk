# Hubbard navigation grouping — 2026-09-07

User requested the 2D and 1D series together under one navigation button.
Completed on [Edukaizen](https://edukaizen.nl/):

- Hubbard (new top-level menu ID 1119, immediately after News)
  - Hubbard 1D (existing ID 332; ten article children)
  - Hubbard 2D (existing custom-link ID 373; six article children)
  - 2D Local Quantum Advantage (existing ID 1109; nine article children)

Hubbard is a grouping link (`#`), not a new content page. Series links still
open their original hubs. All 233 existing page/post content signatures matched
before and after; all 98 existing menu items retained their titles, URLs,
types, attributes and stored order values. Only the parent of items 332, 373
and 1109 changed to 1119. Advantage List stayed separate at stored order 1000.

`navigation_receipt.json` records before/after menu metadata and server checks.
`public_verification.json` confirms the single top-level Hubbard button and
all original links, displayed labels, series order and article parents on
four HTTP-200 pages: homepage plus the three hubs. Visible labels were compared
against the pre-change public HTML because WordPress typographically changes
some raw labels (for example 3x3 to 3×3). `rendered_labels_baseline.json` preserves
that comparison input. Browser interaction/visual QA was unavailable; no
screenshot-based or mobile interaction check is claimed.

A private server-side database backup was taken before changes. The first
preflight aborted before writes because old item 373 is a custom link rather
than a page-linked item. `preflight_recovery.json` records read-only confirmation
of the unchanged menu before proceeding with the exact stored type. No existing
item was recreated and no content or URL was replaced.

The earlier publication receipts remain historical evidence of the state before
this separately requested regrouping. No QPU use or repository visibility
change was performed.
