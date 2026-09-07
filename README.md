# Fermi-Hubbard 2D on IBM Nighthawk

A student-scale 2D quantum-simulation project with a deliberately local goal:
can a quantum computer beat our own classical computer on recorded execution
time, while producing useful observables?

The current narrow timing milestone is about **20x**: the saved classical
chi64 calculation took 150.819 seconds, while two separate 6x6 hardware
experiments recorded 8 and 7 QPU seconds respectively. These are different
timing scopes, not demonstrated end-to-end or matched-accuracy advantage.
The main paired original/compact job is `daf6foe42tqs73avhoeg` on
`ibm_phoenix`; its registered usage was 7 seconds for the whole job, including
both arms and calibration/training circuits. It is not seven seconds per
single circuit. See [the result and claim register](theory/RESULTS_AND_CLAIMS.md).

## Start here

- [Theory and conventions](theory/HANDBOOK.md): Hubbard physics, fermion signs,
  mappings, dynamics, observables, mitigation, and classical complexity.
- [Experiments and result paths](theory/EXPERIMENT_INDEX.md): successes,
  failed controls and alternative mappings stay visible.
- [Edukaizen series 3 drafts](publication/edukaizen_series3/README.md): nine
  Dutch articles and a hub, prepared locally; not published automatically.
- [Google comparison](results_cuprate_2d/google_conversion_2026-09-07_v1/DELIVERY.md):
  actual 5x5 and 6x6 public data, converted to the same observable definitions.
- [Imported project README](archive/imported_root/README.md): the original
  workflow documentation, preserved as historical context.

## What is simulated?

The target is a 6x6 open square lattice, 72 spin-orbitals, N=32 particles,
16 up and 16 down, with four holes in a Neel-background initial state.
Parameters: nearest-neighbour hopping t=1, diagonal hopping t'=-0.25, U=8,
total model time T=0.4, and two symmetric product-formula steps. The selected
full-fermion route retains parity strings, diagonal hopping and interaction.
Older bare-XY/t-only circuits are preserved but are different approximations.

Original and compact in the latest paired run implement the same target
family. One-qubit compilation was simplified; the 20,736 CZ gates were not
removed. The compact result was not more accurate in that test.

## Reproduce without using hardware

This repository retains the source's relative file layout so Python imports
and result references remain usable. On the original Windows machine the
tested interpreter is `/home/bram/.venvs/qiskit/bin/python` in WSL
`Ubuntu-Preview-C`. `requirements-observed.txt` records selected installed
versions; `requirements.txt` is inherited historical configuration, not a
verified fresh-install lockfile.

After cloning, restore the losslessly archived original data if needed:

```bash
python scripts/restore_archives.py --verify
python scripts/restore_archives.py --restore
python -B -m unittest test_google_conversion test_analysis_hardware_compact_tflo
```

The first command validates the archived compressed objects without altering
data. Restoration refuses to overwrite any existing file with different
content. No hardware connection is needed for restoration or these tests.

## Complete local copy, compact GitHub storage

The full source working tree was copied, excluding credentials, interpreter
caches, agent state and the source `.git`. The source project was not moved
or changed. Existing uncommitted source edits were included byte-for-byte.
The import starts a new Git history; its provenance includes the old commit.

Large QPY, NPZ, HDF5 and PDF files remain at their normal local paths. Their
exact bytes are also represented by SHA256-addressed gzip objects split into
parts below 10 MB under `archive/objects/`. `archive/manifest.json` maps every
archived path to its object. Repeated content is stored once. The full copy
manifest is in `migration/source_copy_manifest.json`.

Earlier Fez/Fire Opal data and article packages are historical comparison
material, not Nighthawk results. Inherited deployment workflows were moved
to `archive/legacy_workflows/`; pushing this repository does not publish a
website or submit a quantum job. Third-party sources retain their authorship
and licenses; no new blanket license is assigned to imported material.

## Hardware and publication safety

No new job is authorized by creating or cloning this repository. Old approval
files are historical receipts, not reusable permission. Every new submission
requires a fresh explicit backend, budget and shot authorization. Do not
remove attempt markers or resubmit uncertain jobs. Never commit credentials.

Series 3 is a draft package. Publishing WordPress pages, changing site menus,
making this repository public or enabling GitHub Pages are separate actions.
