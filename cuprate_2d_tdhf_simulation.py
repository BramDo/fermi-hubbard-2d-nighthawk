#!/usr/bin/env python3
"""Fast 2D time-dependent Hartree-Fock run for the cuprate Hubbard target.

This is a classical simulation baseline for the separate 2D cuprate pipeline.
It evolves spin-up and spin-down Slater determinants under the mean-field
decoupling

    U n_up n_down -> U (n_up <n_down> + <n_up> n_down - <n_up><n_down>).

It is useful for charge/spin dynamics and bookkeeping checks on a 6x6 target.
It is not a replacement for DMRG, AFQMC, DCA, or hardware measurements of
off-diagonal d-wave pair correlations.
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

from cuprate_2d_hubbard_pipeline import (
    Cuprate2DConfig,
    all_hopping_bonds,
    initial_site_rows,
    validate_config,
)


def load_config(path: Path) -> Cuprate2DConfig:
    raw = json.loads(path.read_text())
    return Cuprate2DConfig(
        lx=int(raw["lx"]),
        ly=int(raw["ly"]),
        holes=int(raw["holes"]),
        hopping_t=float(raw["hopping_t"]),
        t_prime_over_t=float(raw["t_prime_over_t"]),
        u_over_t=float(raw["u_over_t"]),
        chemical_potential=float(raw["chemical_potential"]),
        steps=int(raw["steps"]),
        dt=float(raw["dt"]),
        boundary_x=str(raw["boundary_x"]),
        boundary_y=str(raw["boundary_y"]),
        initial_state=str(raw["initial_state"]),
        shots=int(raw.get("shots", 20_000)),
    )


def hopping_matrix(cfg: Cuprate2DConfig) -> np.ndarray:
    matrix = np.zeros((cfg.sites, cfg.sites), dtype=np.complex128)
    for bond in all_hopping_bonds(cfg):
        a = int(bond["site_a"])
        b = int(bond["site_b"])
        coefficient = float(bond["coefficient"])
        matrix[a, b] = coefficient
        matrix[b, a] = coefficient
    return matrix


def initial_orbitals(cfg: Cuprate2DConfig) -> tuple[np.ndarray, np.ndarray]:
    rows = initial_site_rows(cfg)
    up_sites = [int(row["site"]) for row in rows if int(row["n_up_initial"])]
    down_sites = [int(row["site"]) for row in rows if int(row["n_down_initial"])]
    identity = np.eye(cfg.sites, dtype=np.complex128)
    return identity[:, up_sites], identity[:, down_sites]


def densities(up_orbitals: np.ndarray, down_orbitals: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n_up = np.sum(np.abs(up_orbitals) ** 2, axis=1).real
    n_down = np.sum(np.abs(down_orbitals) ** 2, axis=1).real
    return n_up, n_down


def apply_hermitian_step(hamiltonian: np.ndarray, orbitals: np.ndarray, dt: float) -> np.ndarray:
    if orbitals.shape[1] == 0:
        return orbitals
    eigvals, eigvecs = np.linalg.eigh(hamiltonian)
    phases = np.exp(-1j * eigvals * dt)
    return eigvecs @ (phases[:, None] * (eigvecs.conj().T @ orbitals))


def orthonormalize(orbitals: np.ndarray) -> np.ndarray:
    if orbitals.shape[1] == 0:
        return orbitals
    q, r = np.linalg.qr(orbitals)
    phases = np.sign(np.diag(r).real)
    phases[phases == 0] = 1.0
    return q * phases


def unitary_mean_field_step(
    cfg: Cuprate2DConfig,
    up_orbitals: np.ndarray,
    down_orbitals: np.ndarray,
    base_hamiltonian: np.ndarray,
    dt: float,
) -> tuple[np.ndarray, np.ndarray]:
    n_up, n_down = densities(up_orbitals, down_orbitals)
    h_up = base_hamiltonian + np.diag(cfg.interaction_u * n_down - cfg.chemical_potential)
    h_down = base_hamiltonian + np.diag(cfg.interaction_u * n_up - cfg.chemical_potential)
    up_next = apply_hermitian_step(h_up, up_orbitals, dt)
    down_next = apply_hermitian_step(h_down, down_orbitals, dt)
    return orthonormalize(up_next), orthonormalize(down_next)


def snapshot_rows(cfg: Cuprate2DConfig, step_index: int, time_value: float, n_up: np.ndarray, n_down: np.ndarray) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for site in range(cfg.sites):
        x = site % cfg.lx
        y = site // cfg.lx
        up = float(n_up[site])
        down = float(n_down[site])
        charge = up + down
        rows.append(
            {
                "step": step_index,
                "time": time_value,
                "site": site,
                "x": x,
                "y": y,
                "n_up": up,
                "n_down": down,
                "charge": charge,
                "spin_z": up - down,
                "hole_density": 1.0 - charge,
                "double_occupancy_mean_field": up * down,
            }
        )
    return rows


def evolve_tdhf(cfg: Cuprate2DConfig, internal_dt: float) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    base_hamiltonian = hopping_matrix(cfg)
    up, down = initial_orbitals(cfg)
    target_times = [(step, step * cfg.dt) for step in range(cfg.steps + 1)]
    rows: list[dict[str, Any]] = []

    start = time.perf_counter()
    current_time = 0.0
    internal_steps = 0
    for target_step, target_time in target_times:
        while current_time < target_time - 1e-12:
            step_dt = min(internal_dt, target_time - current_time)
            up, down = unitary_mean_field_step(cfg, up, down, base_hamiltonian, step_dt)
            current_time += step_dt
            internal_steps += 1
        n_up, n_down = densities(up, down)
        rows.extend(snapshot_rows(cfg, target_step, target_time, n_up, n_down))

    elapsed = time.perf_counter() - start
    final_rows = rows[-cfg.sites :]
    initial_rows = rows[: cfg.sites]
    diagnostics = {
        "elapsed_seconds": elapsed,
        "internal_dt": internal_dt,
        "internal_steps": internal_steps,
        "initial_total_charge": sum(float(row["charge"]) for row in initial_rows),
        "final_total_charge": sum(float(row["charge"]) for row in final_rows),
        "initial_total_spin_z": sum(float(row["spin_z"]) for row in initial_rows),
        "final_total_spin_z": sum(float(row["spin_z"]) for row in final_rows),
        "max_abs_charge_change": max(
            abs(float(final["charge"]) - float(initial["charge"]))
            for initial, final in zip(initial_rows, final_rows, strict=True)
        ),
        "max_abs_spin_change": max(
            abs(float(final["spin_z"]) - float(initial["spin_z"]))
            for initial, final in zip(initial_rows, final_rows, strict=True)
        ),
        "mean_final_double_occupancy_mean_field": float(
            np.mean([float(row["double_occupancy_mean_field"]) for row in final_rows])
        ),
    }
    return rows, diagnostics


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def rows_to_grids(cfg: Cuprate2DConfig, rows: list[dict[str, Any]], step: int, field: str) -> np.ndarray:
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

    initial_charge = rows_to_grids(cfg, rows, 0, "charge")
    final_charge = rows_to_grids(cfg, rows, cfg.steps, "charge")
    initial_spin = rows_to_grids(cfg, rows, 0, "spin_z")
    final_spin = rows_to_grids(cfg, rows, cfg.steps, "spin_z")
    delta_charge = final_charge - initial_charge
    delta_spin = final_spin - initial_spin

    charge_lim = max(0.15, float(np.max(np.abs(delta_charge))))
    spin_lim = max(0.15, float(np.max(np.abs(final_spin))))
    delta_spin_lim = max(0.15, float(np.max(np.abs(delta_spin))))

    fig, axes = plt.subplots(2, 2, figsize=(9.5, 7.6), dpi=170, constrained_layout=True)
    panels = [
        (axes[0, 0], final_charge, "final charge", "viridis", 0.0, 1.2),
        (axes[0, 1], delta_charge, "delta charge", "coolwarm", -charge_lim, charge_lim),
        (axes[1, 0], final_spin, "final spin z", "coolwarm", -spin_lim, spin_lim),
        (axes[1, 1], delta_spin, "delta spin z", "coolwarm", -delta_spin_lim, delta_spin_lim),
    ]
    for ax, data, title, cmap, vmin, vmax in panels:
        image = ax.imshow(data, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax)
        ax.set_title(title)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_xticks(range(cfg.lx))
        ax.set_yticks(range(cfg.ly))
        fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    fig.suptitle(
        f"2D TDHF Hubbard: {cfg.lx}x{cfg.ly}, holes={cfg.holes}, U/t={cfg.u_over_t:g}, "
        f"t'/t={cfg.t_prime_over_t:g}, T={cfg.total_time:g}"
    )
    fig.savefig(path)
    plt.close(fig)
    return path


def write_report(
    path: Path,
    cfg: Cuprate2DConfig,
    diagnostics: dict[str, Any],
    csv_path: Path,
    summary_path: Path,
    plot_path: Path | None,
) -> None:
    lines = [
        "# 2D Cuprate Hubbard TDHF Simulation",
        "",
        "This is a fast classical mean-field simulation for the separate 2D cuprate target.",
        "It is useful for charge/spin dynamics and pipeline checks, not for a superconductivity claim.",
        "",
        "## Target",
        "",
        f"- lattice: {cfg.lx}x{cfg.ly}",
        f"- sites/qubits in matching JW target: {cfg.sites}/{cfg.qubits}",
        f"- holes/doping: {cfg.holes}/{cfg.hole_doping:.6f}",
        f"- U/t: {cfg.u_over_t:g}",
        f"- t'/t: {cfg.t_prime_over_t:g}",
        f"- steps/dt/time: {cfg.steps}/{cfg.dt:g}/{cfg.total_time:g}",
        "",
        "## Diagnostics",
        "",
        f"- elapsed seconds: {diagnostics['elapsed_seconds']:.6f}",
        f"- internal steps: {diagnostics['internal_steps']}",
        f"- total charge initial/final: {diagnostics['initial_total_charge']:.12g}/{diagnostics['final_total_charge']:.12g}",
        f"- total spin-z initial/final: {diagnostics['initial_total_spin_z']:.12g}/{diagnostics['final_total_spin_z']:.12g}",
        f"- max abs charge change: {diagnostics['max_abs_charge_change']:.6g}",
        f"- max abs spin-z change: {diagnostics['max_abs_spin_change']:.6g}",
        f"- mean final double occupancy, mean-field: {diagnostics['mean_final_double_occupancy_mean_field']:.6g}",
        "",
        "## Artifacts",
        "",
        f"- observables CSV: `{csv_path.as_posix()}`",
        f"- summary JSON: `{summary_path.as_posix()}`",
    ]
    if plot_path is not None:
        lines.append(f"- plot: `{plot_path.as_posix()}`")
    lines += [
        "",
        "Claim boundary: TDHF discards connected many-body correlations and cannot establish d-wave superconductivity.",
        "",
    ]
    path.write_text("\n".join(lines))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a 2D cuprate Hubbard TDHF simulation.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--internal-dt", type=float, default=0.005)
    parser.add_argument("--steps", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    if args.steps is not None:
        cfg = replace(cfg, steps=int(args.steps))
    validate_config(cfg)
    if args.internal_dt <= 0:
        raise ValueError("--internal-dt must be positive")

    args.outdir.mkdir(parents=True, exist_ok=True)
    rows, diagnostics = evolve_tdhf(cfg, internal_dt=float(args.internal_dt))
    csv_path = args.outdir / "cuprate_2d_tdhf_observables.csv"
    summary_path = args.outdir / "cuprate_2d_tdhf_summary.json"
    plot_candidate = args.outdir / "cuprate_2d_tdhf_charge_spin.png"
    report_path = args.outdir / "cuprate_2d_tdhf_report.md"

    write_csv(csv_path, rows)
    summary_path.write_text(
        json.dumps(
            {
                "simulation_kind": "time_dependent_hartree_fock",
                "claim_boundary": (
                    "Classical mean-field baseline only. Use DMRG/AFQMC/DCA or hardware "
                    "off-diagonal correlator measurements for superconductivity claims."
                ),
                "config": asdict(cfg),
                "diagnostics": diagnostics,
            },
            indent=2,
        )
        + "\n"
    )
    plot_path = write_plot(plot_candidate, cfg, rows)
    write_report(report_path, cfg, diagnostics, csv_path, summary_path, plot_path)
    print(report_path)


if __name__ == "__main__":
    main()
