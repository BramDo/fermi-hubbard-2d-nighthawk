#!/usr/bin/env python3
"""Compare 2D cuprate site observables over time against a reference source."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from typing import Any

from compare_cuprate_2d_observables import SITE_FIELDS, normalize_site_row, read_csv, write_csv


SUMMARY_FIELDS = [
    "source",
    "profile",
    "step",
    "time",
    "sites",
    "total_charge",
    "total_spin_z",
    "mean_charge",
    "mean_abs_spin_z",
    "mean_double_occupancy",
    "min_charge",
    "max_charge",
]

RMSE_FIELDS = [
    "source",
    "profile",
    "reference",
    "step",
    "time",
    "sites",
    "n_up_rmse",
    "n_down_rmse",
    "charge_rmse",
    "spin_z_rmse",
    "hole_density_rmse",
    "double_occupancy_rmse",
]


def normalize_time_series(source: str, profile: str, path: Path) -> list[dict[str, Any]]:
    rows = []
    for row in read_csv(path):
        if "step" not in row:
            raise ValueError(f"{path} is missing a step column")
        step = int(float(row["step"]))
        rows.append(normalize_site_row(source, profile, row, step=step))
    return rows


def source_profile_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["source"]), str(row["profile"])


def group_by_source_step(rows: list[dict[str, Any]]) -> dict[tuple[str, str, int], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    for row in rows:
        key = (str(row["source"]), str(row["profile"]), int(row["step"]))
        grouped.setdefault(key, []).append(row)
    return grouped


def summarize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries = []
    for (source, profile, step), group in sorted(group_by_source_step(rows).items()):
        charges = [float(row["charge"]) for row in group]
        spins = [float(row["spin_z"]) for row in group]
        doubles = [float(row["double_occupancy"]) for row in group]
        times = sorted({str(row["time"]) for row in group})
        summaries.append(
            {
                "source": source,
                "profile": profile,
                "step": step,
                "time": times[0] if len(times) == 1 else ",".join(times),
                "sites": len(group),
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


def rmse_by_step(rows: list[dict[str, Any]], reference_source: str) -> list[dict[str, Any]]:
    grouped = group_by_source_step(rows)
    references: dict[int, tuple[tuple[str, str, int], dict[int, dict[str, Any]]]] = {}
    for key, group in grouped.items():
        source, _profile, step = key
        if source == reference_source:
            references[step] = (key, {int(row["site"]): row for row in group})

    rmses = []
    for key, group in sorted(grouped.items()):
        source, profile, step = key
        if step not in references or source == reference_source:
            continue
        reference_key, reference = references[step]
        values = {int(row["site"]): row for row in group}
        common = sorted(set(reference) & set(values))
        if not common:
            continue
        row = {
            "source": source,
            "profile": profile,
            "reference": f"{reference_key[0]}:{reference_key[1]}",
            "step": step,
            "time": sorted({str(values[site]["time"]) for site in common})[0],
            "sites": len(common),
        }
        for field in ["n_up", "n_down", "charge", "spin_z", "hole_density", "double_occupancy"]:
            errors = [(float(values[site][field]) - float(reference[site][field])) ** 2 for site in common]
            row[f"{field}_rmse"] = math.sqrt(sum(errors) / len(errors))
        rmses.append(row)
    return rmses


def write_report(path: Path, summaries: list[dict[str, Any]], rmses: list[dict[str, Any]], reference_source: str, artifacts: dict[str, str]) -> None:
    lines = [
        "# 3x3 2D Cuprate Time Sweep",
        "",
        f"Reference source for RMSE: `{reference_source}`.",
        "All rows use diagonal site observables only: charge, spin-z, hole density, and doublon.",
        "",
        "## RMSE by Step",
        "",
        "| step | source | profile | charge RMSE | spin-z RMSE | doublon RMSE |",
        "|---:|---|---|---:|---:|---:|",
    ]
    for row in rmses:
        lines.append(
            f"| {row['step']} | {row['source']} | {row['profile']} | "
            f"{row['charge_rmse']:.6f} | {row['spin_z_rmse']:.6f} | {row['double_occupancy_rmse']:.6f} |"
        )

    lines += [
        "",
        "## Site Summary by Step",
        "",
        "| step | source | profile | total charge | total spin-z | mean |spin-z| | mean doublon |",
        "|---:|---|---|---:|---:|---:|---:|",
    ]
    for row in summaries:
        lines.append(
            f"| {row['step']} | {row['source']} | {row['profile']} | "
            f"{row['total_charge']:.6f} | {row['total_spin_z']:.6f} | "
            f"{row['mean_abs_spin_z']:.6f} | {row['mean_double_occupancy']:.6f} |"
        )

    lines += [
        "",
        "## Artifacts",
        "",
    ]
    for label, artifact in artifacts.items():
        lines.append(f"- {label}: `{artifact}`")
    lines += [
        "",
        "Claim boundary: this is a local small-rung diagonal-observable time sweep. It is not a hardware result and it does not measure off-diagonal d-wave pairing.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--reference-source", default="exact_full")
    parser.add_argument(
        "--site-source",
        action="append",
        required=True,
        help="Time-series site source as source:profile:path. Use relative WSL paths to avoid Windows drive-colon ambiguity.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    site_rows: list[dict[str, Any]] = []
    for spec in args.site_source:
        source, profile, raw_path = str(spec).split(":", 2)
        path = Path(raw_path)
        if not path.exists():
            raise FileNotFoundError(path)
        site_rows.extend(normalize_time_series(source, profile, path))
    if not site_rows:
        raise ValueError("No site rows loaded")

    args.outdir.mkdir(parents=True, exist_ok=True)
    site_path = args.outdir / "cuprate_2d_time_sweep_site_observables.csv"
    summary_path = args.outdir / "cuprate_2d_time_sweep_summary.csv"
    rmse_path = args.outdir / "cuprate_2d_time_sweep_rmse.csv"
    report_path = args.outdir / "cuprate_2d_time_sweep_report.md"

    summaries = summarize_rows(site_rows)
    rmses = rmse_by_step(site_rows, args.reference_source)
    write_csv(site_path, site_rows, SITE_FIELDS)
    write_csv(summary_path, summaries, SUMMARY_FIELDS)
    write_csv(rmse_path, rmses, RMSE_FIELDS)
    write_report(
        report_path,
        summaries,
        rmses,
        args.reference_source,
        {
            "site observables": site_path.as_posix(),
            "summary CSV": summary_path.as_posix(),
            "RMSE CSV": rmse_path.as_posix(),
        },
    )
    print(report_path)


if __name__ == "__main__":
    main()
