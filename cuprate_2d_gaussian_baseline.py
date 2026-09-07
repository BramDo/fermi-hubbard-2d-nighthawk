#!/usr/bin/env python3
"""Gaussian/Majorana-style baseline for the 2D cuprate Hubbard target.

This propagates the quadratic U=0 part of the same t-t' Hubbard model exactly
at the one-particle level. It is equivalent to a free-fermion Gaussian
simulation and serves as a Majorana-style noninteracting baseline for charge and
spin dynamics. It is not a simulation of the interacting U/t=8 problem.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import numpy as np

from cuprate_2d_hubbard_pipeline import Cuprate2DConfig, all_hopping_bonds, initial_site_rows, validate_config
from cuprate_2d_qiskit_circuit import load_config


def hopping_matrix(cfg: Cuprate2DConfig) -> np.ndarray:
    h = np.zeros((cfg.sites, cfg.sites), dtype=np.complex128)
    for bond in all_hopping_bonds(cfg):
        a = int(bond["site_a"])
        b = int(bond["site_b"])
        coefficient = float(bond["coefficient"])
        h[a, b] = coefficient
        h[b, a] = coefficient
    if cfg.chemical_potential:
        h -= cfg.chemical_potential * np.eye(cfg.sites, dtype=np.complex128)
    return h


def initial_orbitals(cfg: Cuprate2DConfig) -> tuple[np.ndarray, np.ndarray]:
    rows = initial_site_rows(cfg)
    up_sites = [int(row["site"]) for row in rows if int(row["n_up_initial"])]
    down_sites = [int(row["site"]) for row in rows if int(row["n_down_initial"])]
    identity = np.eye(cfg.sites, dtype=np.complex128)
    return identity[:, up_sites], identity[:, down_sites]


def evolve_orbitals(h: np.ndarray, orbitals: np.ndarray, time_value: float) -> np.ndarray:
    if orbitals.shape[1] == 0:
        return orbitals
    eigvals, eigvecs = np.linalg.eigh(h)
    phases = np.exp(-1j * eigvals * time_value)
    return eigvecs @ (phases[:, None] * (eigvecs.conj().T @ orbitals))


def densities(up_orbitals: np.ndarray, down_orbitals: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return np.sum(np.abs(up_orbitals) ** 2, axis=1).real, np.sum(np.abs(down_orbitals) ** 2, axis=1).real


def snapshot_rows(cfg: Cuprate2DConfig, step: int, time_value: float, n_up: np.ndarray, n_down: np.ndarray) -> list[dict[str, Any]]:
    rows = []
    for site in range(cfg.sites):
        x = site % cfg.lx
        y = site // cfg.lx
        up = float(n_up[site])
        down = float(n_down[site])
        charge = up + down
        rows.append(
            {
                "step": step,
                "time": time_value,
                "site": site,
                "x": x,
                "y": y,
                "n_up": up,
                "n_down": down,
                "charge": charge,
                "spin_z": up - down,
                "hole_density": 1.0 - charge,
                "double_occupancy_gaussian_product": up * down,
            }
        )
    return rows


def run_gaussian(cfg: Cuprate2DConfig) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    h = hopping_matrix(cfg)
    up0, down0 = initial_orbitals(cfg)
    rows: list[dict[str, Any]] = []
    start = time.perf_counter()
    for step in range(cfg.steps + 1):
        time_value = step * cfg.dt
        up = evolve_orbitals(h, up0, time_value)
        down = evolve_orbitals(h, down0, time_value)
        n_up, n_down = densities(up, down)
        rows.extend(snapshot_rows(cfg, step, time_value, n_up, n_down))
    elapsed = time.perf_counter() - start
    initial = rows[: cfg.sites]
    final = rows[-cfg.sites :]
    diagnostics = {
        "elapsed_seconds": elapsed,
        "total_charge_initial": float(sum(row["charge"] for row in initial)),
        "total_charge_final": float(sum(row["charge"] for row in final)),
        "total_spin_z_initial": float(sum(row["spin_z"] for row in initial)),
        "total_spin_z_final": float(sum(row["spin_z"] for row in final)),
        "max_abs_charge_change": float(max(abs(final_row["charge"] - initial_row["charge"]) for initial_row, final_row in zip(initial, final, strict=True))),
        "max_abs_spin_z_change": float(max(abs(final_row["spin_z"] - initial_row["spin_z"]) for initial_row, final_row in zip(initial, final, strict=True))),
        "mean_final_double_occupancy_gaussian_product": float(np.mean([row["double_occupancy_gaussian_product"] for row in final])),
    }
    return rows, diagnostics


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def rows_to_grid(cfg: Cuprate2DConfig, rows: list[dict[str, Any]], step: int, field: str) -> np.ndarray:
    grid = np.zeros((cfg.ly, cfg.lx), dtype=float)
    for row in rows:
        if int(row["step"]) == step:
            grid[int(row["y"]), int(row["x"])] = float(row[field])
    return grid


def write_plot(path: Path, cfg: Cuprate2DConfig, rows: list[dict[str, Any]]) -> Path | None:
    try:
        import matplotlib.pyplot as plt
    except ModuleNotFoundError:
        return None

    charge = rows_to_grid(cfg, rows, cfg.steps, "charge")
    spin = rows_to_grid(cfg, rows, cfg.steps, "spin_z")
    delta_charge = charge - rows_to_grid(cfg, rows, 0, "charge")
    delta_spin = spin - rows_to_grid(cfg, rows, 0, "spin_z")
    charge_lim = max(0.15, float(np.max(np.abs(delta_charge))))
    spin_lim = max(0.15, float(np.max(np.abs(spin))))
    delta_spin_lim = max(0.15, float(np.max(np.abs(delta_spin))))

    fig, axes = plt.subplots(2, 2, figsize=(9.5, 7.6), dpi=170, constrained_layout=True)
    panels = [
        (axes[0, 0], charge, "final charge, U=0", "viridis", 0.0, 1.2),
        (axes[0, 1], delta_charge, "delta charge, U=0", "coolwarm", -charge_lim, charge_lim),
        (axes[1, 0], spin, "final spin z, U=0", "coolwarm", -spin_lim, spin_lim),
        (axes[1, 1], delta_spin, "delta spin z, U=0", "coolwarm", -delta_spin_lim, delta_spin_lim),
    ]
    for ax, data, title, cmap, vmin, vmax in panels:
        image = ax.imshow(data, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax)
        ax.set_title(title)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_xticks(range(cfg.lx))
        ax.set_yticks(range(cfg.ly))
        fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    fig.suptitle(f"Gaussian/Majorana baseline: {cfg.lx}x{cfg.ly}, t'/t={cfg.t_prime_over_t:g}, T={cfg.total_time:g}")
    fig.savefig(path)
    plt.close(fig)
    return path


def write_report(path: Path, cfg: Cuprate2DConfig, diagnostics: dict[str, Any], csv_path: Path, json_path: Path, plot_path: Path | None) -> None:
    lines = [
        "# 2D Cuprate Hubbard Gaussian/Majorana Baseline",
        "",
        "This is an exact free-fermion baseline for the U=0 part of the same t-t' model.",
        "",
        f"- lattice/qubits: {cfg.lx}x{cfg.ly} / {cfg.qubits}",
        f"- holes/doping: {cfg.holes}/{cfg.hole_doping:.6f}",
        f"- simulated interaction: U/t = 0 baseline; target U/t = {cfg.u_over_t:g}",
        f"- t'/t: {cfg.t_prime_over_t:g}",
        f"- steps/dt/time: {cfg.steps}/{cfg.dt:g}/{cfg.total_time:g}",
        "",
        "## Diagnostics",
        "",
        f"- elapsed seconds: {diagnostics['elapsed_seconds']:.6f}",
        f"- total charge initial/final: {diagnostics['total_charge_initial']:.12g}/{diagnostics['total_charge_final']:.12g}",
        f"- total spin-z initial/final: {diagnostics['total_spin_z_initial']:.12g}/{diagnostics['total_spin_z_final']:.12g}",
        f"- max abs charge change: {diagnostics['max_abs_charge_change']:.6g}",
        f"- max abs spin-z change: {diagnostics['max_abs_spin_z_change']:.6g}",
        f"- mean final double occupancy product: {diagnostics['mean_final_double_occupancy_gaussian_product']:.6g}",
        "",
        "## Artifacts",
        "",
        f"- observables CSV: `{csv_path.as_posix()}`",
        f"- summary JSON: `{json_path.as_posix()}`",
    ]
    if plot_path is not None:
        lines.append(f"- plot: `{plot_path.as_posix()}`")
    lines += [
        "",
        "Claim boundary: this baseline ignores U and cannot replace the interacting 72q circuit or tensor-network benchmarks.",
        "",
    ]
    path.write_text("\n".join(lines))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    if args.steps is not None:
        cfg = replace(cfg, steps=int(args.steps))
    validate_config(cfg)
    args.outdir.mkdir(parents=True, exist_ok=True)
    rows, diagnostics = run_gaussian(cfg)
    csv_path = args.outdir / "cuprate_2d_gaussian_observables.csv"
    json_path = args.outdir / "cuprate_2d_gaussian_summary.json"
    plot_candidate = args.outdir / "cuprate_2d_gaussian_charge_spin.png"
    report_path = args.outdir / "cuprate_2d_gaussian_report.md"
    write_csv(csv_path, rows)
    write_json = {
        "simulation_kind": "gaussian_majorana_free_fermion_u0",
        "claim_boundary": "Exact quadratic U=0 baseline only; target interacting model has U/t > 0.",
        "config": asdict(cfg),
        "simulated_u_over_t": 0.0,
        "target_u_over_t": cfg.u_over_t,
        "diagnostics": diagnostics,
    }
    json_path.write_text(json.dumps(write_json, indent=2, sort_keys=True) + "\n")
    plot_path = write_plot(plot_candidate, cfg, rows)
    write_report(report_path, cfg, diagnostics, csv_path, json_path, plot_path)
    print(report_path)


if __name__ == "__main__":
    main()
