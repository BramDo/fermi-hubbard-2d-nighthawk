#!/usr/bin/env python3
"""Build a no-submit validation ladder for the 2D cuprate Hubbard route.

The ladder targets the current failure mode: the 6x6 one-step circuit is too
deep for useful particle-sector survival. It prepares smaller geometries with
the same observable definitions and a more abstract Fire Opal dry-run input.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from compare_cuprate_2d_observables import normalize_site_row, rmse_rows, summary_rows, write_csv as write_normalized_csv
from cuprate_2d_fire_opal_runner import (
    build_groups,
    circuit_metadata,
    fire_opal_input_strategy,
    write_plan as write_fire_opal_plan,
    write_qasm_manifest,
)
from cuprate_2d_gaussian_baseline import run_gaussian
from cuprate_2d_hubbard_pipeline import (
    Cuprate2DConfig,
    all_hopping_bonds,
    initial_site_rows,
    mode_order,
    observable_plan,
    resource_estimate,
    validate_config,
    write_initial_state_plot,
    write_observable_flat_csv,
)
from cuprate_2d_qiskit_circuit import build_circuit
from cuprate_2d_tdhf_simulation import evolve_tdhf
from ibm_staged_fermi_hubbard_runner import summarize_circuit


LADDER_FIELDS = [
    "label",
    "lx",
    "ly",
    "sites",
    "qubits",
    "holes",
    "doping",
    "steps",
    "dt",
    "nearest_bonds",
    "next_nearest_bonds",
    "pauli_terms_per_step",
    "logical_depth",
    "logical_two_qubit_depth",
    "logical_two_qubit_count",
    "qelib_depth",
    "qelib_two_qubit_depth",
    "qelib_two_qubit_count",
    "abstract_qasm_characters",
    "qelib_qasm_characters",
    "tdhf_mean_doublon",
    "gaussian_mean_doublon",
    "gaussian_charge_rmse_vs_tdhf",
    "gaussian_spin_z_rmse_vs_tdhf",
    "gaussian_doublon_rmse_vs_tdhf",
    "fire_opal_abstract_for_fire_opal",
    "case_dir",
]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def hole_count(lx: int, ly: int, target_doping: float) -> int:
    sites = lx * ly
    holes = max(1, int(round(target_doping * sites)))
    return min(holes, sites - 1)


def default_ladder(target_doping: float) -> list[Cuprate2DConfig]:
    geometry = [(2, 3), (3, 3), (4, 4), (6, 6)]
    return [
        Cuprate2DConfig(
            lx=lx,
            ly=ly,
            holes=hole_count(lx, ly, target_doping),
            hopping_t=1.0,
            t_prime_over_t=-0.25,
            u_over_t=8.0,
            chemical_potential=0.0,
            steps=1,
            dt=0.1,
            boundary_x="open",
            boundary_y="open",
            initial_state="stripe_neel",
            shots=20_000,
        )
        for lx, ly in geometry
    ]


def select_ladder(configs: list[Cuprate2DConfig], only: list[str] | None) -> list[Cuprate2DConfig]:
    if not only:
        return configs
    requested = {item.lower().replace(" ", "") for item in only}
    selected = [cfg for cfg in configs if f"{cfg.lx}x{cfg.ly}" in requested or case_label(cfg) in requested]
    missing = sorted(requested - {f"{cfg.lx}x{cfg.ly}" for cfg in selected} - {case_label(cfg) for cfg in selected})
    if missing:
        available = ", ".join(f"{cfg.lx}x{cfg.ly}" for cfg in configs)
        raise ValueError(f"Unknown ladder rung(s): {', '.join(missing)}. Available: {available}")
    return selected


def case_label(cfg: Cuprate2DConfig) -> str:
    return f"cuprate_{cfg.lx}x{cfg.ly}_holes{cfg.holes}_steps{cfg.steps}"


def normalize_time_rows(source: str, rows: list[dict[str, Any]], profile: str, final_step: int) -> list[dict[str, Any]]:
    selected = [row for row in rows if int(float(row["step"])) == final_step]
    return [normalize_site_row(source, profile, {key: str(value) for key, value in row.items()}, step=final_step) for row in selected]


def final_summary(rows: list[dict[str, Any]], double_key: str) -> dict[str, float]:
    charges = [float(row["charge"]) for row in rows]
    spins = [float(row["spin_z"]) for row in rows]
    doubles = [float(row[double_key]) for row in rows]
    return {
        "total_charge": sum(charges),
        "total_spin_z": sum(spins),
        "mean_abs_spin_z": sum(abs(value) for value in spins) / len(spins),
        "mean_double_occupancy": sum(doubles) / len(doubles),
    }


def write_case_report(
    path: Path,
    *,
    cfg: Cuprate2DConfig,
    row: dict[str, Any],
    artifacts: dict[str, str],
    fire_opal_strategy: dict[str, Any],
) -> None:
    lines = [
        f"# 2D Cuprate Validation Case: {row['label']}",
        "",
        "Local dry-run only. No IBM Runtime, Fire Opal, or hardware job was submitted.",
        "",
        "## Target",
        "",
        f"- lattice/sites/qubits: {cfg.lx}x{cfg.ly} / {cfg.sites} / {cfg.qubits}",
        f"- holes/doping: {cfg.holes}/{cfg.hole_doping:.6f}",
        f"- U/t, t'/t: {cfg.u_over_t:g}, {cfg.t_prime_over_t:g}",
        f"- steps/dt/time: {cfg.steps}/{cfg.dt:g}/{cfg.total_time:g}",
        "",
        "## Circuit Resource",
        "",
        f"- logical depth/two-qubit depth/two-qubit count: {row['logical_depth']}/{row['logical_two_qubit_depth']}/{row['logical_two_qubit_count']}",
        f"- qelib depth/two-qubit depth/two-qubit count: {row['qelib_depth']}/{row['qelib_two_qubit_depth']}/{row['qelib_two_qubit_count']}",
        f"- abstract QASM characters: {row['abstract_qasm_characters']}",
        f"- qelib QASM characters: {row['qelib_qasm_characters']}",
        "",
        "## Local Baseline Check",
        "",
        f"- TDHF mean doublon: {row['tdhf_mean_doublon']:.6f}",
        f"- Gaussian mean doublon: {row['gaussian_mean_doublon']:.6f}",
        f"- Gaussian vs TDHF RMSE charge/spin/doublon: {row['gaussian_charge_rmse_vs_tdhf']:.6f}/{row['gaussian_spin_z_rmse_vs_tdhf']:.6f}/{row['gaussian_doublon_rmse_vs_tdhf']:.6f}",
        "",
        "## Fire Opal Input",
        "",
        f"- abstract for Fire Opal: {fire_opal_strategy['abstract_for_fire_opal']}",
        f"- qasm basis: {fire_opal_strategy['qasm_basis']}",
        f"- backend transpile: {fire_opal_strategy['backend_transpile']}",
        f"- warnings: `{fire_opal_strategy['warnings']}`",
        "",
        "## Artifacts",
        "",
    ]
    for label, artifact in artifacts.items():
        lines.append(f"- {label}: `{artifact}`")
    lines += [
        "",
        "Claim boundary: this case is a validation rung. Passing it does not validate the larger 6x6 hardware result.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def fire_opal_dryrun_args(outdir: Path, backend: str, shots: int, readout_shots: int) -> SimpleNamespace:
    args = SimpleNamespace(
        outdir=outdir,
        backend=backend,
        shots=shots,
        readout_shots=readout_shots,
        qasm_basis="native",
        qasm_optimization_level=0,
        backend_transpile=False,
        backend_optimization_level=1,
        backend_transpile_metadata={"enabled": False},
        submit=False,
    )
    args.fire_opal_input_strategy = fire_opal_input_strategy(args)
    return args


def process_case(cfg: Cuprate2DConfig, outdir: Path, *, backend: str, shots: int, readout_shots: int, internal_dt: float) -> dict[str, Any]:
    validate_config(cfg)
    label = case_label(cfg)
    case_dir = outdir / label
    case_dir.mkdir(parents=True, exist_ok=True)

    config_path = case_dir / "cuprate_2d_config.json"
    config_path.write_text(json.dumps(asdict(cfg), indent=2, sort_keys=True) + "\n")
    write_json(case_dir / "cuprate_2d_mode_order.json", mode_order(cfg))
    write_csv(case_dir / "cuprate_2d_initial_state.csv", initial_site_rows(cfg))
    bonds = all_hopping_bonds(cfg)
    write_csv(case_dir / "cuprate_2d_bonds.csv", bonds)
    resources = resource_estimate(cfg, bonds)
    write_json(case_dir / "cuprate_2d_resource_estimate.json", resources)
    plan = observable_plan(cfg, bonds)
    write_json(case_dir / "cuprate_2d_observable_plan.json", plan)
    write_observable_flat_csv(case_dir / "cuprate_2d_observable_plan.csv", plan)
    preview = write_initial_state_plot(case_dir / "cuprate_2d_initial_state.png", cfg, initial_site_rows(cfg))

    tdhf_rows, tdhf_diag = evolve_tdhf(cfg, internal_dt=internal_dt)
    gaussian_rows, gaussian_diag = run_gaussian(cfg)
    write_csv(case_dir / "cuprate_2d_tdhf_observables.csv", tdhf_rows)
    write_csv(case_dir / "cuprate_2d_gaussian_observables.csv", gaussian_rows)
    write_json(case_dir / "cuprate_2d_tdhf_summary.json", {"config": asdict(cfg), "diagnostics": tdhf_diag})
    write_json(case_dir / "cuprate_2d_gaussian_summary.json", {"config": asdict(cfg), "diagnostics": gaussian_diag})

    normalized = []
    normalized.extend(normalize_time_rows("tdhf", tdhf_rows, "mean_field_step1", cfg.steps))
    normalized.extend(normalize_time_rows("gaussian_u0", gaussian_rows, "free_fermion_step1", cfg.steps))
    summaries = summary_rows(normalized)
    rmses = rmse_rows(normalized, "tdhf")
    write_normalized_csv(case_dir / "cuprate_2d_ladder_site_observables_normalized.csv", normalized, list(normalized[0].keys()))
    write_normalized_csv(case_dir / "cuprate_2d_ladder_observable_summary.csv", summaries, list(summaries[0].keys()))
    write_normalized_csv(case_dir / "cuprate_2d_ladder_observable_rmse.csv", rmses, list(rmses[0].keys()))

    logical_circuit, terms = build_circuit(cfg, measured=True)
    logical_summary = summarize_circuit(logical_circuit)

    fire_dir = case_dir / "fire_opal_abstract_dryrun"
    fire_dir.mkdir(parents=True, exist_ok=True)
    fire_args = fire_opal_dryrun_args(fire_dir, backend, shots, readout_shots)
    groups = build_groups(cfg)
    metadata = circuit_metadata(cfg)
    _manifest_path, records = write_qasm_manifest(
        stage_dir=fire_dir,
        groups=groups,
        metadata=metadata,
        basis=fire_args.qasm_basis,
        optimization_level=fire_args.qasm_optimization_level,
        parse_check=True,
    )
    write_fire_opal_plan(stage_dir=fire_dir, cfg=cfg, records=records, args=fire_args)

    qelib_args = SimpleNamespace(
        qasm_basis="qelib",
        qasm_optimization_level=1,
        backend_transpile=False,
        backend_optimization_level=1,
        backend_transpile_metadata={"enabled": False},
        fire_opal_input_strategy={"abstract_for_fire_opal": False},
        backend=backend,
        shots=shots,
        readout_shots=readout_shots,
        submit=False,
    )
    qelib_dir = case_dir / "fire_opal_qelib_reference_dryrun"
    _qelib_manifest, qelib_records = write_qasm_manifest(
        stage_dir=qelib_dir,
        groups=groups,
        metadata=metadata,
        basis="qelib",
        optimization_level=1,
        parse_check=True,
    )

    main_record = next(record for record in records if record["group"] == "main")
    qelib_main_record = next(record for record in qelib_records if record["group"] == "main")
    tdhf_summary = final_summary([row for row in tdhf_rows if int(row["step"]) == cfg.steps], "double_occupancy_mean_field")
    gaussian_summary = final_summary([row for row in gaussian_rows if int(row["step"]) == cfg.steps], "double_occupancy_gaussian_product")
    gaussian_rmse = next(row for row in rmses if row["source"] == "gaussian_u0")

    row = {
        "label": label,
        "lx": cfg.lx,
        "ly": cfg.ly,
        "sites": cfg.sites,
        "qubits": cfg.qubits,
        "holes": cfg.holes,
        "doping": cfg.hole_doping,
        "steps": cfg.steps,
        "dt": cfg.dt,
        "nearest_bonds": len([bond for bond in bonds if bond["family"] == "nearest_t"]),
        "next_nearest_bonds": len([bond for bond in bonds if bond["family"] == "next_nearest_t_prime"]),
        "pauli_terms_per_step": len(terms),
        "logical_depth": logical_summary["depth"],
        "logical_two_qubit_depth": logical_summary["two_qubit_depth"],
        "logical_two_qubit_count": logical_summary["two_qubit_count"],
        "qelib_depth": qelib_main_record["exported_summary"]["depth"],
        "qelib_two_qubit_depth": qelib_main_record["qasm"]["parsed_summary"]["two_qubit_depth"],
        "qelib_two_qubit_count": qelib_main_record["qasm"]["parsed_summary"]["two_qubit_count"],
        "abstract_qasm_characters": main_record["qasm"]["qasm_characters"],
        "qelib_qasm_characters": qelib_main_record["qasm"]["qasm_characters"],
        "tdhf_mean_doublon": tdhf_summary["mean_double_occupancy"],
        "gaussian_mean_doublon": gaussian_summary["mean_double_occupancy"],
        "gaussian_charge_rmse_vs_tdhf": gaussian_rmse["charge_rmse"],
        "gaussian_spin_z_rmse_vs_tdhf": gaussian_rmse["spin_z_rmse"],
        "gaussian_doublon_rmse_vs_tdhf": gaussian_rmse["double_occupancy_rmse"],
        "fire_opal_abstract_for_fire_opal": fire_args.fire_opal_input_strategy["abstract_for_fire_opal"],
        "case_dir": case_dir.as_posix(),
    }
    artifacts = {
        "config": config_path.as_posix(),
        "initial preview": preview.as_posix(),
        "TDHF observables": (case_dir / "cuprate_2d_tdhf_observables.csv").as_posix(),
        "Gaussian observables": (case_dir / "cuprate_2d_gaussian_observables.csv").as_posix(),
        "Fire Opal abstract plan": (fire_dir / "fire_opal_plan.json").as_posix(),
        "Fire Opal abstract manifest": (fire_dir / "fire_opal_qasm_manifest.json").as_posix(),
        "qelib reference manifest": (qelib_dir / "fire_opal_qasm_manifest.json").as_posix(),
    }
    write_case_report(
        case_dir / "validation_case_report.md",
        cfg=cfg,
        row=row,
        artifacts=artifacts,
        fire_opal_strategy=fire_args.fire_opal_input_strategy,
    )
    return row


def write_ladder_report(path: Path, rows: list[dict[str, Any]]) -> None:
    reference = next((row for row in rows if row["lx"] == 6 and row["ly"] == 6), rows[-1])
    lines = [
        "# 2D Cuprate Validation Ladder",
        "",
        "Local planning and baseline validation only. No IBM Runtime, Fire Opal, or hardware job was submitted.",
        "",
        "The ladder reduces circuit depth before another hardware run and prepares abstract Fire Opal dry-run inputs.",
        "",
        "## Ladder Summary",
        "",
        "| case | qubits | holes | doping | logical 2q count | logical 2q depth | qelib 2q count | qelib 2q depth | qelib 2q count vs 6x6 | Gaussian charge RMSE | Gaussian spin RMSE |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    ref_count = float(reference["qelib_two_qubit_count"] or 1.0)
    for row in rows:
        ratio = float(row["qelib_two_qubit_count"]) / ref_count
        lines.append(
            f"| {row['label']} | {row['qubits']} | {row['holes']} | {row['doping']:.6f} | "
            f"{row['logical_two_qubit_count']} | {row['logical_two_qubit_depth']} | "
            f"{row['qelib_two_qubit_count']} | {row['qelib_two_qubit_depth']} | {ratio:.3f} | "
            f"{row['gaussian_charge_rmse_vs_tdhf']:.6f} | {row['gaussian_spin_z_rmse_vs_tdhf']:.6f} |"
        )
    lines += [
        "",
        "## Recommended Hardware Gate",
        "",
        "1. Use the smallest case that exercises both x/y hopping and t' diagonals before retrying 6x6.",
        "2. Prefer the `fire_opal_abstract_dryrun` plans, which use native, non-backend-transpiled QASM.",
        "3. Require sector survival and same-observable RMSE to pass on a small rung before scaling up.",
        "",
        "Interpretation boundary: these are resource and baseline checks, not hardware evidence.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=Path("results_cuprate_2d/validation_ladder_steps1"))
    parser.add_argument("--target-doping", type=float, default=4.0 / 36.0)
    parser.add_argument("--backend", default="ibm_marrakesh")
    parser.add_argument("--shots", type=int, default=1024)
    parser.add_argument("--readout-shots", type=int, default=4096)
    parser.add_argument("--internal-dt", type=float, default=0.005)
    parser.add_argument(
        "--only",
        action="append",
        help="Run only the selected ladder rung, e.g. --only 3x3. Can be repeated.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    configs = select_ladder(default_ladder(float(args.target_doping)), args.only)
    rows = [
        process_case(
            cfg,
            args.outdir,
            backend=args.backend,
            shots=int(args.shots),
            readout_shots=int(args.readout_shots),
            internal_dt=float(args.internal_dt),
        )
        for cfg in configs
    ]
    summary_csv = args.outdir / "validation_ladder_summary.csv"
    summary_json = args.outdir / "validation_ladder_summary.json"
    report_md = args.outdir / "validation_ladder_report.md"
    write_csv(summary_csv, rows, LADDER_FIELDS)
    write_json(summary_json, {"rows": rows})
    write_ladder_report(report_md, rows)
    print(report_md)


if __name__ == "__main__":
    main()
