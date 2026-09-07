#!/usr/bin/env python3
"""Exact fixed-sector 2D cuprate Hubbard baseline for small validation rungs.

For the 3x3, one-hole case the fixed sector is small enough:
C(9, 4)^2 = 15876 states. This script builds the fermionic Hubbard Hamiltonian
in the repository's interleaved row-major JW mode order, evolves the initial
Neel-with-hole product state, and writes the same diagonal observables used by
the hardware comparison path.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import time
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import numpy as np
from scipy.sparse import coo_matrix, csr_matrix
from scipy.sparse.linalg import expm_multiply

from cuprate_2d_hubbard_pipeline import (
    SPIN_DOWN,
    SPIN_UP,
    Cuprate2DConfig,
    all_hopping_bonds,
    initial_site_rows,
    mode_qubit,
    validate_config,
)
from cuprate_2d_qiskit_circuit import load_config


MODEL_FULL = "full_hubbard"
MODEL_T_ONLY = "t_only_hubbard"
SUPPORTED_MODELS = (MODEL_FULL, MODEL_T_ONLY)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def combinations_mask(n_sites: int, particles: int) -> list[int]:
    masks: list[int] = []
    for combo in itertools.combinations(range(n_sites), particles):
        mask = 0
        for site in combo:
            mask |= 1 << site
        masks.append(mask)
    return masks


def full_mask_from_spin_masks(cfg: Cuprate2DConfig, up_mask: int, down_mask: int) -> int:
    full = 0
    for site in range(cfg.sites):
        if (up_mask >> site) & 1:
            full |= 1 << mode_qubit(site, SPIN_UP)
        if (down_mask >> site) & 1:
            full |= 1 << mode_qubit(site, SPIN_DOWN)
    return full


def initial_masks(cfg: Cuprate2DConfig) -> tuple[int, int]:
    up = 0
    down = 0
    for row in initial_site_rows(cfg):
        site = int(row["site"])
        if int(row["n_up_initial"]):
            up |= 1 << site
        if int(row["n_down_initial"]):
            down |= 1 << site
    return up, down


def sector_basis(cfg: Cuprate2DConfig) -> tuple[list[int], dict[int, int], int, int]:
    init_up, init_down = initial_masks(cfg)
    n_up = init_up.bit_count()
    n_down = init_down.bit_count()
    basis: list[int] = []
    for up_mask in combinations_mask(cfg.sites, n_up):
        for down_mask in combinations_mask(cfg.sites, n_down):
            basis.append(full_mask_from_spin_masks(cfg, up_mask, down_mask))
    return basis, {full: index for index, full in enumerate(basis)}, n_up, n_down


def bit(full: int, mode: int) -> int:
    return (full >> mode) & 1


def annihilate_then_create(full: int, create_mode: int, annihilate_mode: int) -> tuple[int, int] | None:
    if bit(full, annihilate_mode) == 0 or bit(full, create_mode) == 1:
        return None
    lower_annihilate = (1 << annihilate_mode) - 1
    sign = -1 if (full & lower_annihilate).bit_count() % 2 else 1
    removed = full ^ (1 << annihilate_mode)
    lower_create = (1 << create_mode) - 1
    sign *= -1 if (removed & lower_create).bit_count() % 2 else 1
    return removed | (1 << create_mode), sign


def onsite_energy(cfg: Cuprate2DConfig, full: int, n_up: int, n_down: int) -> float:
    doublons = 0
    for site in range(cfg.sites):
        doublons += bit(full, mode_qubit(site, SPIN_UP)) * bit(full, mode_qubit(site, SPIN_DOWN))
    return cfg.interaction_u * doublons - cfg.chemical_potential * (n_up + n_down)


def selected_bonds(cfg: Cuprate2DConfig, model: str) -> list[dict[str, Any]]:
    bonds = all_hopping_bonds(cfg)
    if model == MODEL_T_ONLY:
        bonds = [bond for bond in bonds if str(bond["family"]) == "nearest_t"]
    return bonds


def build_hamiltonian(cfg: Cuprate2DConfig, model: str) -> tuple[csr_matrix, dict[str, Any]]:
    basis, index_by_full, n_up, n_down = sector_basis(cfg)
    rows: list[int] = []
    cols: list[int] = []
    data: list[complex] = []
    bonds = selected_bonds(cfg, model)

    for col, full in enumerate(basis):
        diagonal = onsite_energy(cfg, full, n_up, n_down)
        if diagonal:
            rows.append(col)
            cols.append(col)
            data.append(complex(diagonal))
        for bond in bonds:
            coefficient = float(bond["coefficient"])
            site_a = int(bond["site_a"])
            site_b = int(bond["site_b"])
            for spin in (SPIN_UP, SPIN_DOWN):
                qa = mode_qubit(site_a, spin)
                qb = mode_qubit(site_b, spin)
                for create_mode, annihilate_mode in ((qa, qb), (qb, qa)):
                    hopped = annihilate_then_create(full, create_mode, annihilate_mode)
                    if hopped is None:
                        continue
                    target_full, sign = hopped
                    row = index_by_full.get(target_full)
                    if row is None:
                        continue
                    rows.append(row)
                    cols.append(col)
                    data.append(complex(coefficient * sign))

    hamiltonian = coo_matrix((data, (rows, cols)), shape=(len(basis), len(basis)), dtype=np.complex128).tocsr()
    metadata = {
        "basis_dimension": len(basis),
        "n_up": n_up,
        "n_down": n_down,
        "model": model,
        "hopping_bonds": len(bonds),
        "hamiltonian_nnz": int(hamiltonian.nnz),
    }
    return hamiltonian, metadata


def initial_state_vector(cfg: Cuprate2DConfig, basis_index: dict[int, int]) -> np.ndarray:
    up, down = initial_masks(cfg)
    full = full_mask_from_spin_masks(cfg, up, down)
    vector = np.zeros(len(basis_index), dtype=np.complex128)
    vector[basis_index[full]] = 1.0
    return vector


def diagonal_site_rows(cfg: Cuprate2DConfig, basis: list[int], psi: np.ndarray, step: int, time_value: float, profile: str) -> list[dict[str, Any]]:
    probs = np.abs(psi) ** 2
    norm = float(np.sum(probs))
    if norm <= 0.0:
        raise ValueError("State norm vanished")
    probs = probs / norm

    rows = []
    for site in range(cfg.sites):
        n_up = 0.0
        n_down = 0.0
        double = 0.0
        up_mode = mode_qubit(site, SPIN_UP)
        down_mode = mode_qubit(site, SPIN_DOWN)
        for full, prob in zip(basis, probs, strict=True):
            up = bit(full, up_mode)
            down = bit(full, down_mode)
            n_up += float(prob) * up
            n_down += float(prob) * down
            double += float(prob) * up * down
        charge = n_up + n_down
        rows.append(
            {
                "step": step,
                "time": time_value,
                "profile": profile,
                "site": site,
                "x": site % cfg.lx,
                "y": site // cfg.lx,
                "n_up": n_up,
                "n_down": n_down,
                "charge": charge,
                "spin_z": n_up - n_down,
                "hole_density": 1.0 - charge,
                "double_occupancy": double,
            }
        )
    return rows


def diagonal_bond_rows(cfg: Cuprate2DConfig, basis: list[int], psi: np.ndarray, profile: str) -> list[dict[str, Any]]:
    probs = np.abs(psi) ** 2
    norm = float(np.sum(probs))
    probs = probs / norm
    rows = []
    for bond in [bond for bond in all_hopping_bonds(cfg) if str(bond["family"]) == "nearest_t"]:
        site_a = int(bond["site_a"])
        site_b = int(bond["site_b"])
        charge_corr = 0.0
        spin_corr = 0.0
        for full, prob in zip(basis, probs, strict=True):
            n_a_up = bit(full, mode_qubit(site_a, SPIN_UP))
            n_a_down = bit(full, mode_qubit(site_a, SPIN_DOWN))
            n_b_up = bit(full, mode_qubit(site_b, SPIN_UP))
            n_b_down = bit(full, mode_qubit(site_b, SPIN_DOWN))
            charge_a = n_a_up + n_a_down
            charge_b = n_b_up + n_b_down
            spin_a = n_a_up - n_a_down
            spin_b = n_b_up - n_b_down
            charge_corr += float(prob) * charge_a * charge_b
            spin_corr += float(prob) * spin_a * spin_b
        rows.append(
            {
                "profile": profile,
                "orientation": bond["orientation"],
                "site_a": site_a,
                "x_a": int(bond["x_a"]),
                "y_a": int(bond["y_a"]),
                "site_b": site_b,
                "x_b": int(bond["x_b"]),
                "y_b": int(bond["y_b"]),
                "charge_correlation": charge_corr,
                "spin_z_correlation": spin_corr,
            }
        )
    return rows


def summarize_final(cfg: Cuprate2DConfig, rows: list[dict[str, Any]]) -> dict[str, Any]:
    final_rows = [row for row in rows if int(row["step"]) == cfg.steps]
    charges = [float(row["charge"]) for row in final_rows]
    spins = [float(row["spin_z"]) for row in final_rows]
    doubles = [float(row["double_occupancy"]) for row in final_rows]
    return {
        "total_charge": float(sum(charges)),
        "total_spin_z": float(sum(spins)),
        "mean_abs_spin_z": float(np.mean(np.abs(spins))),
        "mean_double_occupancy": float(np.mean(doubles)),
        "min_charge": float(min(charges)),
        "max_charge": float(max(charges)),
    }


def run_exact(cfg: Cuprate2DConfig, model: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    start = time.perf_counter()
    basis, basis_index, n_up, n_down = sector_basis(cfg)
    hamiltonian, metadata = build_hamiltonian(cfg, model)
    psi0 = initial_state_vector(cfg, basis_index)
    generator = -1j * hamiltonian

    site_rows: list[dict[str, Any]] = []
    final_psi = psi0
    norm_by_step: dict[int, float] = {}
    profile = f"exact_{model}"
    for step in range(cfg.steps + 1):
        time_value = step * cfg.dt
        psi = psi0 if step == 0 else expm_multiply(generator * time_value, psi0)
        if step == cfg.steps:
            final_psi = psi
        norm_by_step[step] = float(np.vdot(psi, psi).real)
        site_rows.extend(diagonal_site_rows(cfg, basis, psi, step, time_value, profile))
    bond_rows = diagonal_bond_rows(cfg, basis, final_psi, profile)

    metadata.update(
        {
            "elapsed_seconds": time.perf_counter() - start,
            "norm_by_step": norm_by_step,
            "final_summary": summarize_final(cfg, site_rows),
            "n_up": n_up,
            "n_down": n_down,
        }
    )
    return site_rows, bond_rows, metadata


def write_report(path: Path, cfg: Cuprate2DConfig, model: str, metadata: dict[str, Any], artifacts: dict[str, str]) -> None:
    summary = metadata["final_summary"]
    lines = [
        "# 3x3 Exact Fixed-Sector 2D Cuprate Baseline",
        "",
        "This is an exact diagonal-observable baseline in the fixed particle-number sector.",
        "",
        f"- model: `{model}`",
        f"- lattice/qubits: {cfg.lx}x{cfg.ly} / {cfg.qubits}",
        f"- sector N_up/N_down: {metadata['n_up']}/{metadata['n_down']}",
        f"- basis dimension: {metadata['basis_dimension']}",
        f"- Hamiltonian nnz: {metadata['hamiltonian_nnz']}",
        f"- steps/dt/time: {cfg.steps}/{cfg.dt:g}/{cfg.total_time:g}",
        "",
        "## Final Diagonal Observables",
        "",
        f"- total charge: {summary['total_charge']:.6f}",
        f"- total spin-z: {summary['total_spin_z']:.6f}",
        f"- mean |spin-z|: {summary['mean_abs_spin_z']:.6f}",
        f"- mean doublon: {summary['mean_double_occupancy']:.6f}",
        "",
        "## Artifacts",
        "",
    ]
    for label, artifact in artifacts.items():
        lines.append(f"- {label}: `{artifact}`")
    lines += [
        "",
        "Claim boundary: this validates diagonal short-time many-body observables on the small 3x3 rung. It is not a tensor-network extrapolation and it does not measure off-diagonal d-wave pairing.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--model", choices=SUPPORTED_MODELS, default=MODEL_FULL)
    parser.add_argument("--steps", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    if args.steps is not None:
        cfg = replace(cfg, steps=int(args.steps))
    validate_config(cfg)
    if cfg.sites > 12:
        raise ValueError("Exact fixed-sector baseline is intended for small validation rungs; use <=12 sites.")

    args.outdir.mkdir(parents=True, exist_ok=True)
    site_rows, bond_rows, metadata = run_exact(cfg, args.model)

    site_path = args.outdir / "cuprate_2d_exact_site_observables.csv"
    bond_path = args.outdir / "cuprate_2d_exact_bond_observables.csv"
    summary_path = args.outdir / "cuprate_2d_exact_summary.json"
    report_path = args.outdir / "cuprate_2d_exact_report.md"
    write_csv(site_path, site_rows)
    write_csv(bond_path, bond_rows)
    write_json(
        summary_path,
        {
            "simulation_kind": "exact_fixed_sector_sparse_hubbard",
            "claim_boundary": "Small-rung exact diagonal observables only; no off-diagonal pairing tomography.",
            "config": asdict(cfg),
            "metadata": metadata,
        },
    )
    write_report(
        report_path,
        cfg,
        args.model,
        metadata,
        {
            "site observables": site_path.as_posix(),
            "bond observables": bond_path.as_posix(),
            "summary JSON": summary_path.as_posix(),
        },
    )
    print(report_path)


if __name__ == "__main__":
    main()
