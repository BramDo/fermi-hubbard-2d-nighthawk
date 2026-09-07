#!/usr/bin/env python3
"""Normalize and compare 2D cuprate Hubbard observables across routes."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any


SITE_FIELDS = [
    "source",
    "profile",
    "step",
    "time",
    "site",
    "x",
    "y",
    "n_up",
    "n_down",
    "charge",
    "spin_z",
    "hole_density",
    "double_occupancy",
]

BOND_FIELDS = [
    "source",
    "profile",
    "orientation",
    "site_a",
    "x_a",
    "y_a",
    "site_b",
    "x_b",
    "y_b",
    "charge_correlation",
    "spin_z_correlation",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def canonical_time(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        return f"{float(value):.12g}"
    except (TypeError, ValueError):
        return str(value)


def latest_step(rows: list[dict[str, str]]) -> int | None:
    if not rows or "step" not in rows[0]:
        return None
    return max(int(float(row["step"])) for row in rows)


def normalize_site_row(
    source: str,
    profile: str,
    row: dict[str, str],
    *,
    step: int | None = None,
    time: float | str | None = None,
) -> dict[str, Any]:
    double_key = "double_occupancy"
    if double_key not in row:
        for candidate in ["double_occupancy_mean_field", "double_occupancy_gaussian_product"]:
            if candidate in row:
                double_key = candidate
                break
    return {
        "source": source,
        "profile": profile,
        "step": "" if step is None else step,
        "time": canonical_time(row.get("time", "") if time is None else time),
        "site": int(float(row["site"])),
        "x": int(float(row["x"])),
        "y": int(float(row["y"])),
        "n_up": float(row["n_up"]),
        "n_down": float(row["n_down"]),
        "charge": float(row["charge"]),
        "spin_z": float(row["spin_z"]),
        "hole_density": float(row["hole_density"]),
        "double_occupancy": float(row[double_key]),
    }


def normalize_time_series_site(
    source: str,
    path: Path,
    profile: str,
    *,
    target_step: int | None = None,
    target_time: float | None = None,
) -> list[dict[str, Any]]:
    rows = read_csv(path)
    step = latest_step(rows) if target_step is None else target_step
    if step is not None and rows and "step" in rows[0]:
        picked = [row for row in rows if int(float(row["step"])) == step]
        if not picked:
            raise ValueError(f"No step={step} rows found in {path}")
    else:
        picked = rows
    return [
        normalize_site_row(source, profile, row, step=step, time=target_time)
        for row in picked
    ]


def normalize_hardware_site(
    source: str,
    path: Path,
    *,
    target_step: int | None = None,
    target_time: float | None = None,
) -> list[dict[str, Any]]:
    rows = read_csv(path)
    return [
        normalize_site_row(source, row.get("profile", "raw"), row, step=target_step, time=target_time)
        for row in rows
    ]


def normalize_existing_site(path: Path, *, target_step: int | None = None, target_time: float | None = None) -> list[dict[str, Any]]:
    normalized = []
    for row in read_csv(path):
        step_value = row.get("step", "")
        step = target_step if step_value == "" else int(float(step_value))
        if target_step is not None and step != target_step:
            continue
        row_time = target_time if row.get("time", "") == "" else None
        normalized.append(normalize_site_row(str(row["source"]), str(row["profile"]), row, step=step, time=row_time))
    return normalized


def normalize_bond(source: str, path: Path) -> list[dict[str, Any]]:
    rows = read_csv(path)
    normalized = []
    for row in rows:
        normalized.append(
            {
                "source": source,
                "profile": row.get("profile", "raw"),
                "orientation": row["orientation"],
                "site_a": int(float(row["site_a"])),
                "x_a": int(float(row["x_a"])),
                "y_a": int(float(row["y_a"])),
                "site_b": int(float(row["site_b"])),
                "x_b": int(float(row["x_b"])),
                "y_b": int(float(row["y_b"])),
                "charge_correlation": float(row["charge_correlation"]),
                "spin_z_correlation": float(row["spin_z_correlation"]),
            }
        )
    return normalized


def source_profile_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["source"]), str(row["profile"])


def summary_rows(site_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in site_rows:
        grouped.setdefault(source_profile_key(row), []).append(row)
    summaries = []
    for (source, profile), rows in sorted(grouped.items()):
        charges = [float(row["charge"]) for row in rows]
        spins = [float(row["spin_z"]) for row in rows]
        doubles = [float(row["double_occupancy"]) for row in rows]
        steps = sorted({str(row["step"]) for row in rows})
        times = sorted({str(row["time"]) for row in rows})
        summaries.append(
            {
                "source": source,
                "profile": profile,
                "step": steps[0] if len(steps) == 1 else ",".join(steps),
                "time": times[0] if len(times) == 1 else ",".join(times),
                "sites": len(rows),
                "total_charge": sum(charges),
                "total_spin_z": sum(spins),
                "mean_charge": sum(charges) / len(charges),
                "mean_abs_spin_z": sum(abs(value) for value in spins) / len(spins),
                "mean_double_occupancy": sum(doubles) / len(doubles),
                "min_charge": min(charges),
                "max_charge": max(charges),
            }
        )
    return summaries


def rmse_rows(site_rows: list[dict[str, Any]], reference_source: str) -> list[dict[str, Any]]:
    by_group: dict[tuple[str, str], dict[int, dict[str, Any]]] = {}
    for row in site_rows:
        by_group.setdefault(source_profile_key(row), {})[int(row["site"])] = row
    reference_key = next((key for key in by_group if key[0] == reference_source), None)
    if reference_key is None:
        return []
    reference = by_group[reference_key]
    rows = []
    for key, values in sorted(by_group.items()):
        if key == reference_key:
            continue
        common = sorted(set(reference) & set(values))
        if not common:
            continue
        metric = {"source": key[0], "profile": key[1], "reference": f"{reference_key[0]}:{reference_key[1]}", "sites": len(common)}
        for field in ["n_up", "n_down", "charge", "spin_z", "hole_density", "double_occupancy"]:
            err = [(float(values[site][field]) - float(reference[site][field])) ** 2 for site in common]
            metric[f"{field}_rmse"] = math.sqrt(sum(err) / len(err))
        rows.append(metric)
    return rows


def write_report(path: Path, summaries: list[dict[str, Any]], rmses: list[dict[str, Any]], site_path: Path, bond_path: Path | None) -> None:
    lines = [
        "# 2D Cuprate Observable Comparison",
        "",
        "All sources are normalized to the same site variables: `n_up`, `n_down`, `charge`, `spin_z`, `hole_density`, and `double_occupancy`.",
        "",
        "## Site Summaries",
        "",
        "| source | profile | step | time | total charge | total spin-z | mean abs spin-z | mean doublon |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summaries:
        lines.append(
            f"| {row['source']} | {row['profile']} | {row['step']} | {row['time']} | {row['total_charge']:.6f} | "
            f"{row['total_spin_z']:.6f} | {row['mean_abs_spin_z']:.6f} | {row['mean_double_occupancy']:.6f} |"
        )
    nonempty_times = sorted({str(row["time"]) for row in summaries if str(row["time"])})
    if len(nonempty_times) > 1:
        lines += [
            "",
            "## Time Check",
            "",
            f"Warning: final times differ across sources: `{', '.join(nonempty_times)}`. RMSE values are not an apples-to-apples dynamical comparison unless the selected paths are time-matched.",
        ]
    if rmses:
        lines += [
            "",
            "## RMSE",
            "",
            "| source | profile | reference | charge RMSE | spin-z RMSE | doublon RMSE |",
            "|---|---|---|---:|---:|---:|",
        ]
        for row in rmses:
            lines.append(
                f"| {row['source']} | {row['profile']} | {row['reference']} | "
                f"{row['charge_rmse']:.6f} | {row['spin_z_rmse']:.6f} | {row['double_occupancy_rmse']:.6f} |"
            )
    lines += [
        "",
        "## Artifacts",
        "",
        f"- normalized site observables: `{site_path.as_posix()}`",
    ]
    if bond_path is not None:
        lines.append(f"- normalized bond observables: `{bond_path.as_posix()}`")
    lines += [
        "",
        "Claim boundary: these are diagonal observables only. d-wave pairing still needs separate off-diagonal measurement circuits.",
        "",
    ]
    path.write_text("\n".join(lines))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--reference-source", default="tdhf")
    parser.add_argument("--target-step", type=int, default=None, help="Select this step from time-series sources and annotate hardware rows with it.")
    parser.add_argument("--target-time", type=float, default=None, help="Optional time value used for hardware rows or blank normalized rows.")
    parser.add_argument("--tdhf-path", type=Path, default=None)
    parser.add_argument("--gaussian-path", type=Path, default=None)
    parser.add_argument("--ibm-site-path", type=Path, default=None)
    parser.add_argument("--ibm-bond-path", type=Path, default=None)
    parser.add_argument("--fire-opal-site-path", type=Path, default=None)
    parser.add_argument("--fire-opal-bond-path", type=Path, default=None)
    parser.add_argument(
        "--site-source",
        action="append",
        default=[],
        help="Additional time-series site source as source:profile:path. Use relative WSL paths to avoid Windows drive-colon ambiguity.",
    )
    parser.add_argument(
        "--bond-source",
        action="append",
        default=[],
        help="Additional bond source as source:path. Use relative WSL paths to avoid Windows drive-colon ambiguity.",
    )
    parser.add_argument(
        "--normalized-site-path",
        action="append",
        default=[],
        type=Path,
        help="Additional already-normalized site CSV containing source/profile columns.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dir = args.run_dir
    site_rows: list[dict[str, Any]] = []
    bond_rows: list[dict[str, Any]] = []
    tdhf_path = args.tdhf_path or run_dir / "tdhf_simulation" / "cuprate_2d_tdhf_observables.csv"
    gaussian_path = args.gaussian_path or run_dir / "gaussian_majorana_baseline" / "cuprate_2d_gaussian_observables.csv"
    candidates = [
        ("tdhf", tdhf_path, "mean_field"),
        ("gaussian_u0", gaussian_path, "free_fermion"),
    ]
    for source, path, profile in candidates:
        if path.exists():
            site_rows.extend(normalize_time_series_site(source, path, profile, target_step=args.target_step, target_time=args.target_time))
    for spec in args.site_source:
        source, profile, raw_path = str(spec).split(":", 2)
        path = Path(raw_path)
        if path.exists():
            site_rows.extend(normalize_time_series_site(source, path, profile, target_step=args.target_step, target_time=args.target_time))
    for path in args.normalized_site_path:
        if path.exists():
            site_rows.extend(normalize_existing_site(path, target_step=args.target_step, target_time=args.target_time))

    hardware_candidates = [
        ("ibm", args.ibm_site_path or run_dir / "ibm_hardware_steps1" / "cuprate_2d_ibm_site_observables.csv"),
        ("fire_opal", args.fire_opal_site_path or run_dir / "fire_opal_steps1" / "cuprate_2d_fire_opal_site_observables.csv"),
    ]
    for source, path in hardware_candidates:
        if path.exists():
            site_rows.extend(normalize_hardware_site(source, path, target_step=args.target_step, target_time=args.target_time))

    bond_candidates = [
        ("ibm", args.ibm_bond_path or run_dir / "ibm_hardware_steps1" / "cuprate_2d_ibm_bond_observables.csv"),
        ("fire_opal", args.fire_opal_bond_path or run_dir / "fire_opal_steps1" / "cuprate_2d_fire_opal_bond_observables.csv"),
    ]
    for source, path in bond_candidates:
        if path.exists():
            bond_rows.extend(normalize_bond(source, path))
    for spec in args.bond_source:
        source, raw_path = str(spec).split(":", 1)
        path = Path(raw_path)
        if path.exists():
            bond_rows.extend(normalize_bond(source, path))

    if not site_rows:
        raise ValueError("No site observable files found")

    args.outdir.mkdir(parents=True, exist_ok=True)
    site_path = args.outdir / "cuprate_2d_site_observables_normalized.csv"
    summary_path = args.outdir / "cuprate_2d_observable_summary.csv"
    rmse_path = args.outdir / "cuprate_2d_observable_rmse.csv"
    bond_path = args.outdir / "cuprate_2d_bond_observables_normalized.csv"
    report_path = args.outdir / "cuprate_2d_observable_comparison.md"
    summaries = summary_rows(site_rows)
    rmses = rmse_rows(site_rows, args.reference_source)
    write_csv(site_path, site_rows, SITE_FIELDS)
    write_csv(summary_path, summaries, list(summaries[0].keys()))
    if rmses:
        write_csv(rmse_path, rmses, list(rmses[0].keys()))
    if bond_rows:
        write_csv(bond_path, bond_rows, BOND_FIELDS)
        written_bond_path: Path | None = bond_path
    else:
        written_bond_path = None
    write_report(report_path, summaries, rmses, site_path, written_bond_path)
    print(report_path)


if __name__ == "__main__":
    main()
