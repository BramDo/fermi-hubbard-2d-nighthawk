#!/usr/bin/env python3
"""Postselect 2D cuprate hardware counts by particle-number sector.

This is an offline diagnostic. It reads existing raw IBM/Fire Opal count
artifacts, keeps exact and near particle-number sectors, and compares the same
site observables against a selected local same-step baseline.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

from compare_cuprate_2d_observables import (
    SITE_FIELDS,
    canonical_time,
    normalize_site_row,
    rmse_rows,
    summary_rows,
    write_csv,
)
from cuprate_2d_ibm_hardware_runner import (
    expected_particle_numbers,
    particle_numbers_from_bitstring,
    site_observable_rows,
)
from cuprate_2d_qiskit_circuit import load_config


SECTOR_FIELDS = [
    "source",
    "profile",
    "max_l1_distance",
    "kept_shots",
    "total_shots",
    "kept_fraction",
    "discard_fraction",
    "unique_bitstrings",
    "expected_n_up",
    "expected_n_down",
    "mean_abs_n_up_error",
    "mean_abs_n_down_error",
    "top_particle_sectors",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def compact_bitstring(key: Any, n_qubits: int) -> str:
    if isinstance(key, int):
        return format(key, f"0{n_qubits}b")
    return str(key).replace(" ", "").zfill(n_qubits)


def normalized_counts(counts: Mapping[Any, Any], n_qubits: int) -> dict[str, int]:
    normalized: dict[str, int] = {}
    for key, value in counts.items():
        bitstring = compact_bitstring(key, n_qubits)
        count = int(round(float(value)))
        if count <= 0:
            continue
        normalized[bitstring] = normalized.get(bitstring, 0) + count
    return normalized


def load_ibm_main_counts(path: Path, n_qubits: int) -> tuple[dict[str, int], dict[str, Any]]:
    raw = json.loads(path.read_text())
    pubs = raw.get("pubs", [])
    main_pub = next((pub for pub in pubs if pub.get("role") == "main"), pubs[0] if pubs else None)
    if main_pub is None:
        raise ValueError(f"No IBM main pub found in {path}")
    meta = {"job_id": raw.get("job_id"), "backend": raw.get("backend"), "path": path.as_posix()}
    return normalized_counts(main_pub["counts"], n_qubits), meta


def load_fire_opal_main_counts(path: Path, n_qubits: int) -> tuple[dict[str, int], dict[str, Any]]:
    raw = json.loads(path.read_text())
    main = raw["main"]
    pub = main["pubs"][0]
    meta = {"job_id": main.get("job_id"), "backend": main.get("backend"), "path": path.as_posix()}
    return normalized_counts(pub["counts"], n_qubits), meta


def sector_filter(
    counts: Mapping[str, int],
    cfg: Any,
    *,
    max_l1_distance: int,
) -> tuple[dict[str, int], dict[str, Any]]:
    expected = expected_particle_numbers(cfg)
    total = 0
    kept_total = 0
    abs_up = 0
    abs_down = 0
    kept: dict[str, int] = {}
    hist: dict[tuple[int, int], int] = {}
    for key, value in counts.items():
        bitstring = compact_bitstring(key, cfg.qubits)
        count = int(value)
        if count <= 0:
            continue
        observed = particle_numbers_from_bitstring(bitstring, cfg)
        dist = abs(observed[0] - expected[0]) + abs(observed[1] - expected[1])
        total += count
        hist[observed] = hist.get(observed, 0) + count
        if dist <= max_l1_distance:
            kept[bitstring] = kept.get(bitstring, 0) + count
            kept_total += count
            abs_up += count * abs(observed[0] - expected[0])
            abs_down += count * abs(observed[1] - expected[1])
    top = [
        {"n_up": key[0], "n_down": key[1], "shots": shots}
        for key, shots in sorted(hist.items(), key=lambda item: item[1], reverse=True)[:10]
    ]
    return kept, {
        "max_l1_distance": max_l1_distance,
        "kept_shots": kept_total,
        "total_shots": total,
        "kept_fraction": 0.0 if total <= 0 else kept_total / total,
        "discard_fraction": 1.0 if total <= 0 else 1.0 - kept_total / total,
        "unique_bitstrings": len(kept),
        "expected_n_up": expected[0],
        "expected_n_down": expected[1],
        "mean_abs_n_up_error": None if kept_total <= 0 else abs_up / kept_total,
        "mean_abs_n_down_error": None if kept_total <= 0 else abs_down / kept_total,
        "top_particle_sectors": top,
    }


def normalize_baseline_step(source: str, path: Path, profile: str, wanted_step: int) -> list[dict[str, Any]]:
    rows = read_csv(path)
    picked = [row for row in rows if int(float(row["step"])) == wanted_step]
    if not picked:
        raise ValueError(f"No step={wanted_step} rows found in {path}")
    return [normalize_site_row(source, profile, row, step=wanted_step) for row in picked]


def hardware_site_rows(source: str, profile: str, cfg: Any, counts: Mapping[str, int], *, step: int) -> list[dict[str, Any]]:
    rows = site_observable_rows(cfg, counts, profile=profile, p01=None, p10=None, readout_corrected=False)
    normalized = []
    for row in rows:
        normalized.append(
            {
                "source": source,
                "profile": row["profile"],
                "step": step,
                "time": canonical_time(step * float(cfg.dt)),
                "site": int(row["site"]),
                "x": int(row["x"]),
                "y": int(row["y"]),
                "n_up": float(row["n_up"]),
                "n_down": float(row["n_down"]),
                "charge": float(row["charge"]),
                "spin_z": float(row["spin_z"]),
                "hole_density": float(row["hole_density"]),
                "double_occupancy": float(row["double_occupancy"]),
            }
        )
    return normalized


def finite_or_blank(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    return value


def write_report(
    path: Path,
    *,
    sector_rows: list[dict[str, Any]],
    summaries: list[dict[str, Any]],
    rmses: list[dict[str, Any]],
    artifacts: Mapping[str, str],
    reference_source: str,
    target_step: int,
) -> None:
    lines = [
        "# 2D Cuprate Sector-Conditioned Hardware Comparison",
        "",
        "This report reuses existing raw bitstring counts only. No IBM Runtime, Fire Opal, or hardware job was submitted.",
        "",
        "Postselection is a diagnostic, not mitigation proof: if few shots survive, the resulting observables have high statistical noise.",
        "",
        "## Sector Survival",
        "",
        "| source | profile | kept shots | total shots | kept fraction | discard fraction | unique kept | mean abs dN_up | mean abs dN_down |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in sector_rows:
        lines.append(
            f"| {row['source']} | {row['profile']} | {row['kept_shots']} | {row['total_shots']} | "
            f"{row['kept_fraction']:.6f} | {row['discard_fraction']:.6f} | {row['unique_bitstrings']} | "
            f"{float(row['mean_abs_n_up_error'] or 0.0):.6f} | {float(row['mean_abs_n_down_error'] or 0.0):.6f} |"
        )
    lines += [
        "",
        "## Site Summaries",
        "",
        "| source | profile | total charge | total spin-z | mean abs spin-z | mean doublon | min charge | max charge |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summaries:
        lines.append(
            f"| {row['source']} | {row['profile']} | {row['total_charge']:.6f} | {row['total_spin_z']:.6f} | "
            f"{row['mean_abs_spin_z']:.6f} | {row['mean_double_occupancy']:.6f} | "
            f"{row['min_charge']:.6f} | {row['max_charge']:.6f} |"
        )
    lines += [
        "",
        f"## RMSE vs {reference_source} Step {target_step}",
        "",
        "| source | profile | charge RMSE | spin-z RMSE | doublon RMSE | sites |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in rmses:
        lines.append(
            f"| {row['source']} | {row['profile']} | {row['charge_rmse']:.6f} | "
            f"{row['spin_z_rmse']:.6f} | {row['double_occupancy_rmse']:.6f} | {row['sites']} |"
        )
    lines += [
        "",
        "## Artifacts",
        "",
    ]
    for label, artifact_path in artifacts.items():
        lines.append(f"- {label}: `{artifact_path}`")
    lines += [
        "",
        "Interpretation boundary: sector-conditioned rows are useful to diagnose whether the correct conserved sector contains a TDHF-like signal. They are not standalone physical evidence when survival is small.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=Path("results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111"))
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--outdir", type=Path, default=None)
    parser.add_argument("--tdhf-path", type=Path, default=None)
    parser.add_argument("--gaussian-path", type=Path, default=None)
    parser.add_argument("--reference-source", default="tdhf")
    parser.add_argument("--reference-path", type=Path, default=None)
    parser.add_argument("--target-step", type=int, default=1)
    parser.add_argument("--ibm-raw-path", type=Path, default=None)
    parser.add_argument("--fire-opal-raw-path", type=Path, default=None)
    parser.add_argument("--max-near-distance", type=int, default=2)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dir = args.run_dir
    cfg_path = args.config or run_dir / "cuprate_2d_config.json"
    outdir = args.outdir or run_dir / "sector_conditioned_best_mit"
    outdir.mkdir(parents=True, exist_ok=True)

    cfg = load_config(cfg_path)
    ibm_raw_path = args.ibm_raw_path or run_dir / "ibm_hardware_steps1_best_mit" / "cuprate_2d_ibm_raw_results.json"
    fire_opal_raw_path = args.fire_opal_raw_path or run_dir / "fire_opal_steps1_best_mit" / "fire_opal_raw_results.json"
    sources = []
    if ibm_raw_path.exists():
        sources.append(("ibm", ibm_raw_path, load_ibm_main_counts))
    if fire_opal_raw_path.exists():
        sources.append(("fire_opal", fire_opal_raw_path, load_fire_opal_main_counts))
    if not sources:
        raise FileNotFoundError(f"No raw hardware count files found: {ibm_raw_path} or {fire_opal_raw_path}")

    all_site_rows: list[dict[str, Any]] = []
    sector_rows: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {"config": asdict(cfg), "sources": {}}

    default_tdhf = run_dir / "cuprate_2d_tdhf_observables.csv"
    default_gaussian = run_dir / "cuprate_2d_gaussian_observables.csv"
    tdhf_path = args.tdhf_path or (default_tdhf if default_tdhf.exists() else run_dir / "tdhf_simulation" / "cuprate_2d_tdhf_observables.csv")
    gaussian_path = args.gaussian_path or (
        default_gaussian if default_gaussian.exists() else run_dir / "gaussian_majorana_baseline" / "cuprate_2d_gaussian_observables.csv"
    )
    target_step = int(args.target_step)
    if args.reference_path is not None and args.reference_path.exists():
        all_site_rows.extend(normalize_baseline_step(args.reference_source, args.reference_path, f"reference_step{target_step}", target_step))
    if tdhf_path.exists():
        all_site_rows.extend(normalize_baseline_step("tdhf", tdhf_path, f"mean_field_step{target_step}", target_step))
    if gaussian_path.exists():
        all_site_rows.extend(normalize_baseline_step("gaussian_u0", gaussian_path, f"free_fermion_step{target_step}", target_step))

    for source, raw_path, loader in sources:
        counts, meta = loader(raw_path, cfg.qubits)
        metadata["sources"][source] = meta
        all_site_rows.extend(hardware_site_rows(source, "unfiltered_raw", cfg, counts, step=target_step))
        for distance in range(0, max(0, int(args.max_near_distance)) + 1):
            profile = "exact_sector" if distance == 0 else f"near_sector_l1_le_{distance}"
            kept, sector_meta = sector_filter(counts, cfg, max_l1_distance=distance)
            sector_row = {"source": source, "profile": profile, **sector_meta}
            sector_rows.append(sector_row)
            if kept:
                all_site_rows.extend(hardware_site_rows(source, profile, cfg, kept, step=target_step))

    summaries = summary_rows(all_site_rows)
    rmses = rmse_rows(all_site_rows, args.reference_source)

    site_path = outdir / "sector_conditioned_site_observables.csv"
    summary_path = outdir / "sector_conditioned_observable_summary.csv"
    rmse_path = outdir / "sector_conditioned_observable_rmse.csv"
    sector_path = outdir / "sector_conditioned_sector_summary.csv"
    metadata_path = outdir / "sector_conditioned_metadata.json"
    report_path = outdir / "sector_conditioned_report.md"

    write_csv(site_path, all_site_rows, SITE_FIELDS)
    write_csv(summary_path, summaries, list(summaries[0].keys()))
    write_csv(rmse_path, rmses, list(rmses[0].keys()))
    write_csv(
        sector_path,
        [
            {key: json.dumps(value) if key == "top_particle_sectors" else finite_or_blank(value) for key, value in row.items()}
            for row in sector_rows
        ],
        SECTOR_FIELDS,
    )
    write_json(metadata_path, metadata)
    write_report(
        report_path,
        sector_rows=sector_rows,
        summaries=summaries,
        rmses=rmses,
        artifacts={
            "site observables": site_path.as_posix(),
            "observable summary": summary_path.as_posix(),
            "RMSE": rmse_path.as_posix(),
            "sector summary": sector_path.as_posix(),
            "metadata": metadata_path.as_posix(),
        },
        reference_source=args.reference_source,
        target_step=target_step,
    )
    print(report_path)


if __name__ == "__main__":
    main()
