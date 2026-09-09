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

- [Experimental L-MPF mitigation](theory/LMPF_PROTOCOL.md): offline eight-qubit
  2D Hubbard validation, genuine 2D tensor networks, explicit rejected fits,
  and prepared 3x3/6x6 folding inputs. This is not validated 6x6 hardware mitigation.
  [Executed comparison and verification](results_cuprate_2d/lmpf_2d_pilot_2026-09-08_v3/DELIVERY.md).
  [Actual 3x3 hardware application](results_cuprate_2d/lmpf_3x3_hardware_2026-09-08_v1/DELIVERY.md):
  spin improves, charge and doublons worsen; the conditional 6x6 step was not started.
  [Higher-bond diagnostic](results_cuprate_2d/lmpf_3x3_higher_bond_2026-09-08_v2/DELIVERY.md):
  chi2/4 and a canonical chi8/16 check remain unstable; the native graph is a chain.
  [Chi32/64 continuation](results_cuprate_2d/lmpf_3x3_chi32_64_2026-09-08_v1/DELIVERY.md):
  overlap changes decrease to 1.36%-7.07%, but still miss the fixed stability thresholds.
  [Chi128 continuation](results_cuprate_2d/lmpf_3x3_chi128_2026-09-08_v1/DELIVERY.md):
  central Z_up and Z_down pass the local flags; ZZ still fails at 3.29% Gram change.
  These are coefficient diagnostics, not newly improved hardware measurements.
  [Central ZZ chi256](results_cuprate_2d/lmpf_3x3_zz_chi256_2026-09-09_v1/DELIVERY.md):
  coefficient change passes; full-Gram change is still 1.31%, above 1%.
  The ideal ZZ expectation overshoots the exact reference; large states are losslessly archived.
  [Exact ideal-norm follow-up](results_cuprate_2d/lmpf_3x3_exact_norm_2026-09-09_v1/DELIVERY.md):
  the central exact-norm/G/b stability checks pass; all weights remain unchanged.
  This retrospective diagnostic is not a new hardware improvement or full 3x3 validation.
  [Matching central hardware pilot](results_cuprate_2d/lmpf_3x3_central_hardware_2026-09-09_v1/DELIVERY.md):
  fixed higher-bond weights give negative charge/doublon estimates at matched
  shot budget; no resolved improvement. This pilot does not support 6x6 escalation.
  [Shot-aware regularization](results_cuprate_2d/lmpf_3x3_shot_aware_2026-09-09_v1/DELIVERY.md):
  smaller point errors and sampling spread than the old L-MPF on the same data,
  but negative doublons and no resolved improvement across baselines remain.
  [Archived-twirl reuse check](results_cuprate_2d/lmpf_3x3_twirl_reuse_2026-09-09_v1/DELIVERY.md):
  all 21 comparisons differ internally and as full surrogate channels;
  direct reuse of twirl0 weights is not established. No new hardware scoring.
  [Twirl1 central Z_up](results_cuprate_2d/lmpf_3x3_twirl1_zup_2026-09-09_v1/DELIVERY.md):
  eight new chi64/128 operator states pass the fixed local stability checks;
  63 tests and independent overlap/KKT audit pass. No new hardware values.
  [Twirl1 central Z_down](results_cuprate_2d/lmpf_3x3_twirl1_zdown_2026-09-09_v1/DELIVERY.md):
  the second operator also passes chi64/128, with 67 tests and an independent audit;
  central ZZ and the matching hardware comparison remain pending.
- [Theory and conventions](theory/HANDBOOK.md): Hubbard physics, fermion signs,
  mappings, dynamics, observables, mitigation, and classical complexity.
- [Experiments and result paths](theory/EXPERIMENT_INDEX.md): successes,
  failed controls and alternative mappings stay visible.
- [Recomputed exact 3x3 reference](results_cuprate_2d/exact_3x3_recomputed_2026-09-07_v1/RESULTAAT.md):
  full fixed-sector Hamiltonian evolution at T=0.1, 0.2 and 0.4, with 64 numerical
  checks and saved state vectors. This is separate from the 6x6 MPS reference.
- [Edukaizen series 3](https://edukaizen.nl/2d-local-quantum-advantage/): nine
  Dutch articles and a hub, published with explicit approval on 2026-09-07.
  The [complete English series](https://edukaizen.nl/2d-local-quantum-advantage-en/)
  is also live, with reciprocal Nederlands/English controls on all twenty pages.
  [Sources and publication receipts](publication/edukaizen_series3/README.md).
- [Student Advantage List entry](https://edukaizen.nl/pro-student-quantum-advantage-list/#fermi-hubbard-2d-nighthawk-72q):
  added on 2026-09-07 as a local execution-metric ratio with unvalidated accuracy.
  [Registration and verification](publication/advantage_list/2026-09-07_v1/DELIVERY.md).
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

Series 3 was published on Edukaizen on 2026-09-07 after explicit approval.
The repository remains private. Publishing future changes, making this
repository public or enabling GitHub Pages require separate authorization.
