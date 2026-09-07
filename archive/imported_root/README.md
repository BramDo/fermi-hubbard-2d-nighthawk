# 2D Cuprate Fermi-Hubbard Validation

This repository contains the separate 2D cuprate-oriented Fermi-Hubbard route
split out from the original 1D `fermi-hubbard-60q-tdvp` snapshot.

The current focus is a square-lattice one-band Hubbard workflow with `U/t=8`,
`t'/t=-0.25`, hole doping, local diagonal observables, exact small-rung
validation, tensor-network baselines, IBM hardware diagnostics, and Q-CTRL
Fire Opal diagnostics where available.

## Claim Boundary

The hardware output in this repo is diagnostic until it has been compared with
the local baselines and observable-comparison files.

This repo does not claim:

- d-wave superconductivity
- cuprate material behavior
- practical quantum advantage

The validated interpretation is narrower: circuit, noise, sector-survival, and
same-observable comparisons for a staged 2D Hubbard route.

## Main Workflows

Full fermion signs and interactions (added 2026-09-05):

```powershell
.\scripts\prepare_cuprate_2d_fermionic_dynamics_wsl.ps1 -RoutePhoenix
```

This validates the new `fermionic_jw_symmetric` circuit against independent
Fock-space Hamiltonians and exact evolution on small lattices, then prepares
the 6x6 time series at 2, 4 and 8 steps. It includes row-major Jordan-Wigner
parity strings, nearest and diagonal hopping, onsite U, chemical potential,
and a second-order symmetric product formula. The script cannot submit jobs.
`-RoutePhoenix` only retrieves the backend and transpiles locally. Future ZNE
settings retain 512 shots per noise factor and the 5-second runtime cap.

The historical `number_preserving_*` families remain unchanged for reproducing
the old hardware results. Their bare XY hopping omits nonlocal JW strings;
the `t_only` version also omits diagonal hopping. Their MPS reference cannot
be reused as the reference for the new full-fermion route. The new MPS circuit
simulator supports its CZ, controlled-phase and phase gates. Large-lattice
time-step convergence, tensor convergence and hardware accuracy still need
separate checks before claims about Hubbard dynamics or quantum advantage.

Fermionic mapping optimization (no QPU submission):

```bash
python optimize_cuprate_2d_fermionic_mapping.py \
  --config results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/cuprate_2d_config.json \
  --outdir results_cuprate_2d/fermionic_mapping_2026-09-05
python verify_cuprate_2d_mapping_archive.py \
  --outdir results_cuprate_2d/fermionic_mapping_2026-09-05
```

Run these with the WSL Qiskit interpreter below. `--validate-only` on the
optimizer runs only local numerical checks, without retrieving a backend.
The full run ranks bounded physical-path candidates and compares adaptive
fSWAP routing and parallel fSWAP networks at transpiler levels 1 and 3.
Both keep fermionic signs, t, t-prime, and onsite U. Adaptive routing preserves
the reference finite-step unitary; the network changes the second-order term
ordering and therefore needs its own time-step and tensor-convergence checks.
The selected network reduces the two-step Phoenix circuit from 67,793 to
15,400 CZ gates and from depth 63,098 to 1,853. These are compilation resource
improvements, not measured hardware accuracy or quantum advantage. The saved
plans retain 512 shots per noise factor and a five-second cap; this is not a
claim that the compiled circuits and ZNE overhead will fit that runtime.
The archive includes validation, all candidate metrics, layouts, observables,
coupling/CZ-error snapshots, QPY circuits, and SHA-256 hashes. Large QPY files
are preserved locally but are not included in the Git checkpoint.

Classical baseline screening for that exact mapped network:

```bash
python validate_cuprate_2d_fswap_baseline.py \
  --config results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/cuprate_2d_config.json \
  --outdir results_cuprate_2d/fermionic_baseline_2026-09-05/time0p2_dt0p1 \
  --matching-qpy results_cuprate_2d/fermionic_mapping_2026-09-05/steps2/logical_circuit.qpy
python cuprate_2d_network_mpo_baseline.py \
  --config results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/cuprate_2d_config.json \
  --outdir results_cuprate_2d/fermionic_baseline_2026-09-05/time0p2_dt0p1_mpo \
  --matching-qpy results_cuprate_2d/fermionic_mapping_2026-09-05/steps2/logical_circuit.qpy
```

Both commands run local exact checks before the 72-mode MPS ladder and cannot
submit hardware jobs. They monitor every completed time step, recording
observables, mean spin particle numbers, half-chain entropy and norm lost by
SVD truncation before explicit normalization. The retained norm is a
diagnostic, not fidelity or a certified error bound. Default bond dimensions
are 16, 32 and 64, with a 300-second local time cap per case. Existing matching
case results are reused; changed source/config requires a new output folder.
The second command eliminates routing permutations algebraically and applies
each full JW hopping evolution as a bond-4 MPO. Its untruncated result is the
same network unitary, but finite-bond errors can differ between the two routes.

The screening threshold is 0.001 RMSE and 0.005 maximum site difference for
each of charge, spin-z and double occupancy, plus particle-drift and retained-
norm checks. Two successive bond refinements must pass before a time-step
study can be interpreted as Hamiltonian convergence. Use `--steps 4 --dt 0.05`
and `--steps 8 --dt 0.025` to keep total time 0.2 in that later study, with
separate output folders and no mismatched `--matching-qpy`. A false screening
result is preserved as a diagnostic, never promoted to a validated reference.
The inherited config's `shots` field is unused by these noiseless calculations
and does not change the future hardware settings of 512 shots/factor and 5 s.

Small full-fermion hardware-validation pilot (3x3, 18 qubits, one hole):

```bash
python cuprate_2d_fermionic_pilot.py prepare --outdir results_cuprate_2d/fermionic_pilot_3x3_2026-09-05
python cuprate_2d_fermionic_pilot.py submit --outdir results_cuprate_2d/fermionic_pilot_3x3_2026-09-05
python cuprate_2d_fermionic_pilot.py retrieve --outdir results_cuprate_2d/fermionic_pilot_3x3_2026-09-05
```

`prepare` runs independent exact-Hamiltonian and circuit checks, fixed-time
dt refinement, and full 18-qubit native-circuit state equivalence before
freezing the layout, circuit, references and observables. `submit` is a paid
action requiring user authorization: exactly one ZNE job, 512 shots per factor
(1/3/5), eight twirls of 64 shots, maximum execution time 5 seconds. A saved
submission attempt blocks duplicate submission even if the response was lost.
Never remove this guard to retry; investigate the unique saved job tag first.
`retrieve` is read-only with respect to hardware and saves provider inputs,
metrics, complete results and same-observable comparisons. The factor-1
comparison is unextrapolated but still twirled, not an independent raw job.
The exact finite-step circuit and exact Hamiltonian references remain separate.
This pilot is classically tractable and cannot demonstrate quantum advantage.
The older PEC/ZNE runner hard-codes the shallow t-only circuit and must not be
used to submit this full-fermion pilot.

Prepare the default 6x6 target:

```powershell
.\scripts\run_cuprate_2d_pipeline_wsl.ps1
```

Run the validation ladder:

```powershell
.\scripts\run_cuprate_2d_validation_ladder_wsl.ps1
```

Run local baselines and comparisons:

```powershell
.\scripts\run_cuprate_2d_tdhf_wsl.ps1
.\scripts\run_cuprate_2d_gaussian_wsl.ps1
.\scripts\compare_cuprate_2d_observables_wsl.ps1
```

The Windows wrappers resolve the repo root from their own location and call the
known WSL Qiskit environment:

```text
/home/bram/.venvs/qiskit/bin/python
```

## GitHub Pages

The static project site lives in `docs/` and is designed for GitHub Pages:

```text
https://bramdo.github.io/fermi-hubbard-2d-cuprate/
```

It summarizes the claim boundary, run paths, curated result locations, and the
canonical Edukaizen 2D cuprate article series. The workflow in
`.github/workflows/pages.yml` publishes `docs/` on pushes to `main` once GitHub
Pages is configured to use GitHub Actions.

## Hardware Safety

Scripts named `submit_*` can submit IBM Runtime or Fire Opal jobs. Other scripts
should be treated as local generation, dry-run, retrieval, comparison, or
analysis unless an explicit `--submit` flag is passed.

Before interpreting a hardware result, compare it against the matching local
baseline under `results_cuprate_2d` and check the sector-conditioned report.

## Repository Layout

```text
cuprate_2d_*.py                 2D target, circuits, baselines, IBM/Fire Opal runners
compare_cuprate_2d_*.py         same-observable comparison tools
analyze_cuprate_2d_*.py         sector-conditioned analysis
scripts/                        PowerShell and Bash workflow wrappers
docs/                           2D report and publication builders
results_cuprate_2d/             curated reproducible 2D result snapshot
output/medium_2d_cuprate_series Medium package for the 2D article series
output/wordpress_2d_cuprate_series WordPress package for the 2D article series
```

## Setup

Base Python dependencies:

```bash
python -m pip install -r requirements.txt
```

Optional Fire Opal dependencies:

```bash
python -m pip install -r requirements-fire-opal.txt
```

For this machine, prefer the existing WSL environment above when running Qiskit
or Fire Opal workflows.
