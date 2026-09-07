#!/usr/bin/env python3
"""Optional Frontier-style soft sector decoder for staged Fermi-Hubbard counts.

This module intentionally implements a conservative first step:

    P'(bitstring) proportional to P(bitstring) exp(-lambda * sector_penalty)

where sector_penalty is the squared distance from the target (N_up, N_down)
particle-number sector. It is "Frontier-style" in the limited sense that it
adds a soft detector/constraint factor instead of hard postselection. It is not
a full QEC detector error model and should not be used as standalone evidence
for corrected Fermi-Hubbard dynamics.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from advantage_scale_fermi_hubbard_model import (
    SPIN_DOWN,
    SPIN_UP,
    AdvantageScaleConfig,
    bit_from_qiskit_bitstring,
    expected_neel_particle_numbers,
)


def particle_numbers(
    bitstring: str,
    *,
    cfg: AdvantageScaleConfig,
    cbit_to_mode: Mapping[int, Mapping[str, Any]],
) -> tuple[int, int]:
    n_up = 0
    n_down = 0
    for cbit, mode in cbit_to_mode.items():
        bit = bit_from_qiskit_bitstring(bitstring, int(cbit), cfg.qubits)
        if mode.get("spin") == SPIN_UP:
            n_up += bit
        elif mode.get("spin") == SPIN_DOWN:
            n_down += bit
    return n_up, n_down


def soft_sector_reweight_counts(
    counts: Mapping[str, int | float],
    *,
    cfg: AdvantageScaleConfig,
    cbit_to_mode: Mapping[int, Mapping[str, Any]],
    lambda_sector: float,
    linear_penalty: bool = False,
) -> tuple[dict[str, float], dict[str, Any]]:
    """Return counts reweighted by a soft particle-sector constraint.

    The total shot mass is preserved, but counts become floating weights. This
    keeps downstream expectation-value code unchanged while making the route
    explicitly opt-in and reversible.
    """

    if lambda_sector < 0.0:
        raise ValueError("lambda_sector must be non-negative")

    target_up, target_down = expected_neel_particle_numbers(cfg.sites, cfg.vacancy_site)
    total_input = float(sum(float(value) for value in counts.values()))
    if total_input <= 0.0:
        raise ValueError("counts are empty")

    unscaled: dict[str, float] = {}
    penalty_histogram: dict[str, float] = {}
    weighted_penalty_sum = 0.0
    hard_sector_input_mass = 0.0
    weight_square_mass = 0.0
    min_weight = float("inf")
    max_weight = 0.0

    for bitstring, value in counts.items():
        count = float(value)
        n_up, n_down = particle_numbers(bitstring, cfg=cfg, cbit_to_mode=cbit_to_mode)
        du = int(n_up - target_up)
        dd = int(n_down - target_down)
        penalty = abs(du) + abs(dd) if linear_penalty else du * du + dd * dd
        weight = float(math.exp(-float(lambda_sector) * float(penalty)))
        unscaled[bitstring] = count * weight
        penalty_histogram[str(penalty)] = penalty_histogram.get(str(penalty), 0.0) + count
        weighted_penalty_sum += count * float(penalty)
        weight_square_mass += count * weight * weight
        min_weight = min(min_weight, weight)
        max_weight = max(max_weight, weight)
        if du == 0 and dd == 0:
            hard_sector_input_mass += count

    total_unscaled = float(sum(unscaled.values()))
    if total_unscaled <= 0.0:
        raise ValueError("soft sector reweighting removed all count mass")
    scale = total_input / total_unscaled
    reweighted = {bitstring: float(value * scale) for bitstring, value in unscaled.items()}

    output_hard_sector_mass = 0.0
    weighted_penalty_output = 0.0
    for bitstring, value in reweighted.items():
        n_up, n_down = particle_numbers(bitstring, cfg=cfg, cbit_to_mode=cbit_to_mode)
        du = int(n_up - target_up)
        dd = int(n_down - target_down)
        penalty = abs(du) + abs(dd) if linear_penalty else du * du + dd * dd
        weighted_penalty_output += float(value) * float(penalty)
        if du == 0 and dd == 0:
            output_hard_sector_mass += float(value)

    effective_sample_size = total_unscaled * total_unscaled / max(weight_square_mass, 1e-300)
    return reweighted, {
        "enabled": True,
        "route_name": "frontier_soft_sector",
        "claim_boundary": (
            "Soft particle-sector reweighting diagnostic; not full QEC/DEM Frontier decoding "
            "and not selected as headline by default."
        ),
        "lambda_sector": float(lambda_sector),
        "penalty": "L1" if linear_penalty else "squared_L2",
        "target_n_up": int(target_up),
        "target_n_down": int(target_down),
        "input_total_mass": total_input,
        "output_total_mass": float(sum(reweighted.values())),
        "normalization_scale": scale,
        "hard_sector_input_survival": float(hard_sector_input_mass / total_input),
        "hard_sector_output_mass_fraction": float(output_hard_sector_mass / total_input),
        "mean_input_sector_penalty": float(weighted_penalty_sum / total_input),
        "mean_output_sector_penalty": float(weighted_penalty_output / total_input),
        "effective_sample_size": float(effective_sample_size),
        "effective_sample_fraction": float(effective_sample_size / total_input),
        "min_unscaled_weight": float(min_weight),
        "max_unscaled_weight": float(max_weight),
        "input_penalty_histogram": dict(sorted(penalty_histogram.items(), key=lambda item: int(item[0]))),
    }


def parse_lambda_values(value: str) -> list[float]:
    values = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        values.append(float(part))
    if not values:
        raise argparse.ArgumentTypeError("at least one lambda value is required")
    return values


def profile_value(row: Mapping[str, Any], key: str) -> float | None:
    value = row.get(key)
    if value in {None, ""}:
        return None
    return float(value)


def find_route(route_rows: Iterable[Mapping[str, Any]], profile: str) -> Mapping[str, Any] | None:
    for row in route_rows:
        if row.get("profile") == profile:
            return row
    return None


def run_standalone_analysis(
    *,
    stage_dir: Path,
    lambda_values: list[float],
    reference_observables: Path | None,
    max_noiseless_qubits: int,
    linear_penalty: bool,
) -> tuple[Path, Path, Path]:
    """Run a separate soft-sector comparison without touching old summaries."""

    from summarize_ibm_staged_results import (
        charge_density_from_counts,
        config_from_stage_plan,
        load_external_observable_reference,
        load_submitted_jobs,
        main_counts_by_zne_factor,
        mode_by_classical_bit,
        noiseless_charge_density,
        noiseless_observable_profile,
        observable_profile_from_counts,
        observable_route_rows,
        profile_site_values,
        readout_params,
        repo_relative_path,
        rmse,
        semantic_mapping_from_plan,
    )

    plan = json.loads((stage_dir / "stage_plan.json").read_text())
    raw_results = json.loads((stage_dir / "ibm_staged_raw_results.json").read_text())
    submitted_jobs = load_submitted_jobs(stage_dir)
    cfg = config_from_stage_plan(plan)
    mapping = semantic_mapping_from_plan(plan, cfg)
    cbit_to_mode = mode_by_classical_bit(mapping)
    counts_by_factor = main_counts_by_zne_factor(raw_results, submitted_jobs, cfg)
    counts = counts_by_factor.get(1, next(iter(counts_by_factor.values())))
    p01, p10, readout_meta = readout_params(raw_results, cfg)

    if reference_observables is not None:
        ideal_profile = load_external_observable_reference(reference_observables, cfg)
    else:
        ideal_profile = noiseless_observable_profile(cfg, cbit_to_mode, max_noiseless_qubits)
    ideal_charge = profile_site_values(ideal_profile, "charge")
    if ideal_charge is None and reference_observables is None:
        ideal_charge = noiseless_charge_density(cfg, max_noiseless_qubits)

    baseline_profiles: dict[str, dict[str, Any] | None] = {
        "raw": observable_profile_from_counts(counts, cfg, cbit_to_mode),
        "readout_corrected": None
        if p01 is None or p10 is None
        else observable_profile_from_counts(counts, cfg, cbit_to_mode, p01, p10, readout_corrected=True),
    }
    baseline_rows = observable_route_rows(baseline_profiles, ideal_profile, cfg)
    baseline_readout = find_route(baseline_rows, "readout_corrected")
    baseline_raw = find_route(baseline_rows, "raw")

    rows: list[dict[str, Any]] = []
    best_row: dict[str, Any] | None = None
    metadata_by_lambda: dict[str, Any] = {}
    for lambda_sector in lambda_values:
        soft_counts, metadata = soft_sector_reweight_counts(
            counts,
            cfg=cfg,
            cbit_to_mode=cbit_to_mode,
            lambda_sector=float(lambda_sector),
            linear_penalty=linear_penalty,
        )
        metadata_by_lambda[str(lambda_sector)] = metadata
        charge = charge_density_from_counts(soft_counts, cfg, cbit_to_mode)
        profiles = {
            "frontier_soft_sector_raw": observable_profile_from_counts(soft_counts, cfg, cbit_to_mode),
            "frontier_soft_sector_readout_corrected": None
            if p01 is None or p10 is None
            else observable_profile_from_counts(soft_counts, cfg, cbit_to_mode, p01, p10, readout_corrected=True),
        }
        route_rows = observable_route_rows(profiles, ideal_profile, cfg)
        for route in route_rows:
            row = {
                "lambda_sector": float(lambda_sector),
                "profile": route["profile"],
                "observable_score_vs_reference": route.get("observable_score_vs_noiseless"),
                "occupation_rmse": route.get("occupation_rmse"),
                "charge_rmse": route.get("charge_rmse"),
                "spin_rmse": route.get("spin_rmse"),
                "double_occupancy_rmse": route.get("double_occupancy_rmse"),
                "total_charge_error": route.get("total_charge_error"),
                "total_spin_error": route.get("total_spin_error"),
                "charge_density_rmse": rmse(charge, ideal_charge),
                "hard_sector_output_mass_fraction": metadata["hard_sector_output_mass_fraction"],
                "mean_output_sector_penalty": metadata["mean_output_sector_penalty"],
                "effective_sample_fraction": metadata["effective_sample_fraction"],
                "baseline_raw_score": None
                if baseline_raw is None
                else baseline_raw.get("observable_score_vs_noiseless"),
                "baseline_readout_corrected_score": None
                if baseline_readout is None
                else baseline_readout.get("observable_score_vs_noiseless"),
                "baseline_readout_corrected_charge_rmse": None
                if baseline_readout is None
                else baseline_readout.get("charge_rmse"),
            }
            rows.append(row)
            score = profile_value(row, "observable_score_vs_reference")
            if score is not None and (best_row is None or score < float(best_row["observable_score_vs_reference"])):
                best_row = dict(row)

    csv_path = stage_dir / "ibm_staged_frontier_soft_sector_sweep.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "schema_version": 1,
        "stage_dir": repo_relative_path(stage_dir),
        "method": {
            "name": "frontier_soft_sector",
            "claim_boundary": (
                "Optional soft particle-sector reweighting. This is not full QEC/DEM Frontier decoding "
                "and should not replace the old headline unless separately validated."
            ),
            "linear_penalty": bool(linear_penalty),
            "lambda_values": lambda_values,
        },
        "reference_source": None if ideal_profile is None else ideal_profile.get("reference_source"),
        "readout_available": readout_meta is not None,
        "baseline_raw": baseline_raw,
        "baseline_readout_corrected": baseline_readout,
        "best_soft_sector_row": best_row,
        "metadata_by_lambda": metadata_by_lambda,
        "rows": rows,
    }
    json_path = stage_dir / "ibm_staged_frontier_soft_sector_sweep.json"
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    md_path = stage_dir / "ibm_staged_frontier_soft_sector_sweep.md"
    lines = [
        "# Frontier Soft-Sector Sweep",
        "",
        "Optional diagnostic only. Existing raw/readout results are not modified by this artifact.",
        "",
        f"- stage dir: `{repo_relative_path(stage_dir)}`",
        f"- baseline raw score: {None if baseline_raw is None else baseline_raw.get('observable_score_vs_noiseless')}",
        f"- baseline readout-corrected score: {None if baseline_readout is None else baseline_readout.get('observable_score_vs_noiseless')}",
        f"- baseline readout-corrected charge RMSE: {None if baseline_readout is None else baseline_readout.get('charge_rmse')}",
        f"- best soft-sector row: `{None if best_row is None else best_row.get('profile')}` at lambda {None if best_row is None else best_row.get('lambda_sector')}",
        "",
        "| lambda | profile | score | charge RMSE | spin RMSE | total charge err | hard-sector mass | ESS frac |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {lambda_sector:.6g} | {profile} | {score} | {charge} | {spin} | {total_charge} | {hard_mass:.6f} | {ess:.6f} |".format(
                lambda_sector=float(row["lambda_sector"]),
                profile=row["profile"],
                score=row["observable_score_vs_reference"],
                charge=row["charge_rmse"],
                spin=row["spin_rmse"],
                total_charge=row["total_charge_error"],
                hard_mass=float(row["hard_sector_output_mass_fraction"]),
                ess=float(row["effective_sample_fraction"]),
            )
        )
    lines.extend(
        [
            "",
            "Verdict rule: a lower score is only a diagnostic improvement. Do not use this as headline physics without hold-out validation.",
            "",
        ]
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage-dir", type=Path, default=Path("data/hardware/baseline_dd_twirling"))
    parser.add_argument(
        "--lambda-values",
        type=parse_lambda_values,
        default=parse_lambda_values("0,0.005,0.01,0.02,0.05,0.1,0.2,0.5,1.0"),
        help="Comma-separated soft-sector lambda values.",
    )
    parser.add_argument("--reference-observables", type=Path, default=None)
    parser.add_argument("--max-noiseless-qubits", type=int, default=24)
    parser.add_argument("--linear-penalty", action="store_true", help="Use |dN_up|+|dN_down| instead of squared penalty.")
    args = parser.parse_args()

    csv_path, json_path, md_path = run_standalone_analysis(
        stage_dir=args.stage_dir,
        lambda_values=args.lambda_values,
        reference_observables=args.reference_observables,
        max_noiseless_qubits=args.max_noiseless_qubits,
        linear_penalty=args.linear_penalty,
    )
    print(f"Wrote {csv_path}")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
