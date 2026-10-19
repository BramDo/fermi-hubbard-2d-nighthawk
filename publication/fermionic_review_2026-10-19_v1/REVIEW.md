# Fermionic Circuit and Publication Review

19 October 2026. No QPU submission or new hardware authorization.

The public cuprate repository is the July historical snapshot. The separate
private Nighthawk repository already contains full-fermion dynamics, mapping,
TFLO and MPS implementation. Its September archive and the October measurements
must not be presented as the same run. Repository visibility is unchanged.

See [the route register](../../docs/FERMIONIC_ROUTES.md), the small exact
statevector check in `physics_checks.json`, and the source/blob comparison in
`audit_summary.json`. The check is small-lattice verification, not a new 6x6
convergence or hardware-accuracy certificate.

The October curve values are copied without refitting from the archived
`sparse_doublon_chi128_plot_2026-10-05_v1/plotted_local_values.csv`.
At T=0.8, chi128 gives mean D=0.072687424; chi64 gives 0.061595521 and diagnostic
hardware readout+TFLO gives 0.147333202. Four October jobs used 24 QPU seconds
in total, including controls. Independent U=0/TFLO screens failed; neither
chi64 nor chi128 is certified converged. No Google-matched accuracy, universal
factor-two observable error, or matched-accuracy advantage is established.

## Publication Procedure

- Inventory current GitHub heads, visibility, WordPress IDs, parents and content.
- Preserve preimages locally in ignored `private_backup/`; keep a private server
  database backup before any WordPress update.
- Public GitHub receives only a historical warning, route register and Pages
  notice. No private research code/data are made public.
- Private Nighthawk receives the register, October scalar values and small exact
  check. Do not overwrite its existing README or historical experiment archive.
- Update the existing 1D hub, seven historical 2D pages and twenty Nighthawk
  pages with dated notices. Keep their original bodies, IDs, URLs, language
  controls, formulas, navigation, historical numbers and titles intact.
- GitHub writes are narrow tree commits with expected-parent checks and no
  force push. Existing run artifacts and source hashes remain unchanged.
- Record commit receipts, server write checks and public HTTP verification in
  this release. Older publication packages are superseded for live-page updates;
  do not blindly regenerate or republish a September package over these notices.
