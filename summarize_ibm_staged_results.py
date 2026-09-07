#!/usr/bin/env python3
"""Summarize staged IBM Runtime Fermi-Hubbard results.

This post-processing step is separate from submission on purpose. It can fetch
finished Runtime jobs from submitted_jobs.json, or reuse a saved raw-results
JSON, and writes charge-density plus echo-depth artifacts for inspection.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Mapping

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from qiskit.quantum_info import Statevector

from advantage_scale_fermi_hubbard_model import (
    SPIN_DOWN,
    SPIN_UP,
    AdvantageScaleConfig,
    MitigationConfig,
    bit_from_qiskit_bitstring,
    build_main_circuit,
    estimate_local_readout_params,
    expected_neel_particle_numbers,
    initial_logical_bits,
    mitigated_z_expectation_from_counts,
    pair_interleaved_qubit,
    qiskit_counts_key_from_logical_bits,
    semantic_mapping_manifest,
)
from ibm_staged_fermi_hubbard_runner import build_runtime_service, stage_echo_steps
from frontier_soft_sector_decoder import soft_sector_reweight_counts


def repo_relative_path(path: Path | str | None, base: Path | None = None) -> str | None:
    if path is None:
        return None
    root = (base or Path.cwd()).resolve()
    candidate = Path(path)
    try:
        return candidate.resolve().relative_to(root).as_posix()
    except Exception:
        return candidate.as_posix()


def display_reference_source(value: Any) -> Any:
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    if value == "internal_statevector":
        return value
    if "/" in value or "\\" in value:
        return repo_relative_path(value)
    return value


def config_from_stage_plan(plan: Mapping[str, Any]) -> AdvantageScaleConfig:
    cfg_data = dict(plan["config"])
    mitigation_data = dict(cfg_data.pop("mitigation", {}))
    return AdvantageScaleConfig(**cfg_data, mitigation=MitigationConfig(**mitigation_data))


def semantic_mapping_from_plan(plan: Mapping[str, Any], cfg: AdvantageScaleConfig) -> dict[str, Any]:
    mapping = plan.get("semantic_mapping")
    if isinstance(mapping, dict):
        return dict(mapping)
    fallback = semantic_mapping_manifest(cfg)
    fallback["mapping_source"] = "derived_from_config_for_legacy_stage_plan"
    fallback["warning"] = (
        "stage_plan.json did not contain semantic_mapping; postprocessing derived "
        "the q[i] -> c[i] mapping from the current scaffold conventions."
    )
    return fallback


def mode_by_classical_bit(mapping: Mapping[str, Any]) -> dict[int, dict[str, Any]]:
    raw = mapping.get("classical_bit_to_mode", {})
    by_bit: dict[int, dict[str, Any]] = {}
    if isinstance(raw, dict):
        for key, value in raw.items():
            by_bit[int(key)] = dict(value)
    return by_bit


def initial_bits_from_mapping(mapping: Mapping[str, Any], cfg: AdvantageScaleConfig) -> list[int]:
    bits = mapping.get("initial_logical_bits_q0_first")
    if isinstance(bits, list) and len(bits) == cfg.qubits:
        return [int(bit) for bit in bits]
    return initial_logical_bits(cfg)


def initial_qiskit_key_from_mapping(mapping: Mapping[str, Any], cfg: AdvantageScaleConfig) -> str:
    key = mapping.get("initial_qiskit_counts_key")
    if isinstance(key, str) and len(key.replace(" ", "")) == cfg.qubits:
        return clean_bitstring(key, cfg.qubits)
    return qiskit_counts_key_from_logical_bits(initial_bits_from_mapping(mapping, cfg))


def clean_bitstring(bitstring: Any, n_qubits: int) -> str:
    if isinstance(bitstring, int):
        return format(bitstring, f"0{n_qubits}b")
    return str(bitstring).replace(" ", "").zfill(n_qubits)


def normalize_counts(counts: Mapping[Any, Any], n_qubits: int) -> dict[str, int]:
    normalized: dict[str, int] = {}
    for key, value in counts.items():
        bitstring = clean_bitstring(key, n_qubits)
        normalized[bitstring] = normalized.get(bitstring, 0) + int(round(float(value)))
    return dict(sorted(normalized.items()))


def counts_from_pub_result(pub_result: Any, n_qubits: int) -> dict[str, int]:
    data = getattr(pub_result, "data", None)
    if data is None:
        raise ValueError("Runtime pub result has no data field")

    candidates = []
    if hasattr(data, "meas"):
        candidates.append(getattr(data, "meas"))
    if hasattr(data, "__dict__"):
        candidates.extend(vars(data).values())
    for attr in dir(data):
        if attr.startswith("_") or attr == "meas":
            continue
        try:
            candidates.append(getattr(data, attr))
        except Exception:
            continue

    for candidate in candidates:
        if hasattr(candidate, "get_counts"):
            return normalize_counts(candidate.get_counts(), n_qubits)
    raise ValueError("Could not find a measured register with get_counts()")


def iter_pub_results(result: Any) -> list[Any]:
    try:
        return list(result)
    except TypeError:
        try:
            return [result[index] for index in range(len(result))]
        except Exception:
            return [result]


def fetch_raw_results(stage_dir: Path, n_qubits: int) -> dict[str, Any]:
    submitted_path = stage_dir / "submitted_jobs.json"
    if not submitted_path.exists():
        raise FileNotFoundError(f"Missing {submitted_path}")

    submitted = json.loads(submitted_path.read_text())
    service = build_runtime_service()
    raw: dict[str, Any] = {}
    for group_name, record in submitted.items():
        job_id = record.get("job_id")
        group_raw: dict[str, Any] = {
            "job_id": job_id,
            "backend": record.get("backend"),
            "status": "not_submitted" if not job_id else "unknown",
            "pubs": [],
        }
        if not job_id:
            raw[group_name] = group_raw
            continue

        job = service.job(job_id)
        try:
            group_raw["status"] = str(job.status()).split(".")[-1]
        except Exception:
            group_raw["status"] = "unknown"
        primitive_result = job.result()
        pubs = []
        for index, pub_result in enumerate(iter_pub_results(primitive_result)):
            counts = counts_from_pub_result(pub_result, n_qubits)
            pubs.append(
                {
                    "index": index,
                    "shots": int(sum(counts.values())),
                    "unique_bitstrings": len(counts),
                    "counts": counts,
                }
            )
        group_raw["pubs"] = pubs
        raw[group_name] = group_raw
    return raw


def load_raw_results(stage_dir: Path, n_qubits: int, raw_results_path: Path | None, refresh: bool) -> dict[str, Any]:
    cache_path = stage_dir / "ibm_staged_raw_results.json"
    if raw_results_path is not None:
        raw = json.loads(raw_results_path.read_text())
    elif cache_path.exists() and not refresh:
        raw = json.loads(cache_path.read_text())
    else:
        raw = fetch_raw_results(stage_dir, n_qubits)
    cache_path.write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n")
    return raw


def charge_density_from_counts(
    counts: Mapping[str, int],
    cfg: AdvantageScaleConfig,
    cbit_to_mode: Mapping[int, Mapping[str, Any]],
) -> list[float]:
    shots = float(sum(counts.values()))
    if shots <= 0.0:
        raise ValueError("Counts are empty")
    charge = np.zeros(cfg.sites, dtype=float)
    for bitstring, value in counts.items():
        weight = float(value) / shots
        for cbit, mode in cbit_to_mode.items():
            site = int(mode["site"])
            charge[site] += weight * bit_from_qiskit_bitstring(bitstring, cbit, cfg.qubits)
    return [float(value) for value in charge]


def readout_corrected_charge_density(
    counts: Mapping[str, int],
    cfg: AdvantageScaleConfig,
    cbit_to_mode: Mapping[int, Mapping[str, Any]],
    p01: np.ndarray,
    p10: np.ndarray,
) -> list[float]:
    charge = []
    for site in range(cfg.sites):
        site_charge = 0.0
        for cbit, mode in cbit_to_mode.items():
            if int(mode["site"]) != site:
                continue
            z_exp, _ = mitigated_z_expectation_from_counts(
                counts,
                qubits=[cbit],
                num_qubits=cfg.qubits,
                p01=p01,
                p10=p10,
            )
            site_charge += 0.5 * (1.0 - z_exp)
        charge.append(float(site_charge))
    return charge


def z_expectation_from_counts(counts: Mapping[str, int], cbit: int, n_qubits: int) -> float:
    shots = float(sum(counts.values()))
    if shots <= 0.0:
        raise ValueError("Counts are empty")
    z_sum = 0.0
    for bitstring, value in counts.items():
        bit = bit_from_qiskit_bitstring(bitstring, cbit, n_qubits)
        z_sum += float(value) * (1.0 if bit == 0 else -1.0)
    return float(z_sum / shots)


def z_product_expectation_from_counts(counts: Mapping[str, float], cbits: list[int], n_qubits: int) -> float:
    shots = float(sum(float(value) for value in counts.values()))
    if shots <= 0.0:
        raise ValueError("Counts are empty")
    z_sum = 0.0
    for bitstring, value in counts.items():
        product = 1.0
        for cbit in cbits:
            bit = bit_from_qiskit_bitstring(bitstring, cbit, n_qubits)
            product *= 1.0 if bit == 0 else -1.0
        z_sum += float(value) * product
    return float(z_sum / shots)


def z_product_expectation(
    counts: Mapping[str, int],
    cbits: list[int],
    cfg: AdvantageScaleConfig,
    p01: np.ndarray | None,
    p10: np.ndarray | None,
    *,
    readout_corrected: bool,
) -> float:
    if readout_corrected and p01 is not None and p10 is not None:
        z_exp, _ = mitigated_z_expectation_from_counts(
            counts,
            qubits=cbits,
            num_qubits=cfg.qubits,
            p01=p01,
            p10=p10,
        )
        return float(z_exp)
    return z_product_expectation_from_counts(counts, cbits, cfg.qubits)


def site_spin_cbits(
    cfg: AdvantageScaleConfig,
    cbit_to_mode: Mapping[int, Mapping[str, Any]],
) -> list[dict[str, int]]:
    sites = [{SPIN_UP: None, SPIN_DOWN: None} for _ in range(cfg.sites)]
    for cbit, mode in cbit_to_mode.items():
        site = int(mode["site"])
        spin = str(mode["spin"])
        if spin in {SPIN_UP, SPIN_DOWN}:
            sites[site][spin] = int(cbit)
    missing = [
        (site, spin)
        for site, spins in enumerate(sites)
        for spin in (SPIN_UP, SPIN_DOWN)
        if spins[spin] is None
    ]
    if missing:
        raise ValueError(f"semantic mapping is missing site/spin classical bits: {missing}")
    return [{SPIN_UP: int(spins[SPIN_UP]), SPIN_DOWN: int(spins[SPIN_DOWN])} for spins in sites]


def onsite_observables_from_z(zu: float, zd: float, zud: float) -> dict[str, float]:
    n_up = 0.5 * (1.0 - zu)
    n_down = 0.5 * (1.0 - zd)
    return {
        "n_up": float(n_up),
        "n_down": float(n_down),
        "charge": float(n_up + n_down),
        "spin": float(n_up - n_down),
        "double_occupancy": float(0.25 * (1.0 - zu - zd + zud)),
    }


def observable_profile_from_counts(
    counts: Mapping[str, int],
    cfg: AdvantageScaleConfig,
    cbit_to_mode: Mapping[int, Mapping[str, Any]],
    p01: np.ndarray | None = None,
    p10: np.ndarray | None = None,
    *,
    readout_corrected: bool = False,
) -> dict[str, Any]:
    site_cbits = site_spin_cbits(cfg, cbit_to_mode)
    site_rows = []
    for site, spins in enumerate(site_cbits):
        up = spins[SPIN_UP]
        down = spins[SPIN_DOWN]
        zu = z_product_expectation(counts, [up], cfg, p01, p10, readout_corrected=readout_corrected)
        zd = z_product_expectation(counts, [down], cfg, p01, p10, readout_corrected=readout_corrected)
        zud = z_product_expectation(counts, [up, down], cfg, p01, p10, readout_corrected=readout_corrected)
        row = {"site": site, **onsite_observables_from_z(zu, zd, zud)}
        site_rows.append(row)

    nn_charge_corr = []
    nn_spin_corr = []
    for site in range(cfg.sites - 1):
        left = site_cbits[site]
        right = site_cbits[site + 1]
        left_modes = [left[SPIN_UP], left[SPIN_DOWN]]
        right_modes = [right[SPIN_UP], right[SPIN_DOWN]]
        charge_pair = 0.0
        for a in left_modes:
            za = z_product_expectation(counts, [a], cfg, p01, p10, readout_corrected=readout_corrected)
            for b in right_modes:
                zb = z_product_expectation(counts, [b], cfg, p01, p10, readout_corrected=readout_corrected)
                zab = z_product_expectation(counts, [a, b], cfg, p01, p10, readout_corrected=readout_corrected)
                charge_pair += 0.25 * (1.0 - za - zb + zab)
        zd_l_zd_r = z_product_expectation(
            counts, [left[SPIN_DOWN], right[SPIN_DOWN]], cfg, p01, p10, readout_corrected=readout_corrected
        )
        zd_l_zu_r = z_product_expectation(
            counts, [left[SPIN_DOWN], right[SPIN_UP]], cfg, p01, p10, readout_corrected=readout_corrected
        )
        zu_l_zd_r = z_product_expectation(
            counts, [left[SPIN_UP], right[SPIN_DOWN]], cfg, p01, p10, readout_corrected=readout_corrected
        )
        zu_l_zu_r = z_product_expectation(
            counts, [left[SPIN_UP], right[SPIN_UP]], cfg, p01, p10, readout_corrected=readout_corrected
        )
        nn_charge_corr.append(float(charge_pair))
        nn_spin_corr.append(float(0.25 * (zd_l_zd_r - zd_l_zu_r - zu_l_zd_r + zu_l_zu_r)))

    charges = np.asarray([row["charge"] for row in site_rows], dtype=float)
    spins = np.asarray([row["spin"] for row in site_rows], dtype=float)
    doubles = np.asarray([row["double_occupancy"] for row in site_rows], dtype=float)
    parity = np.asarray([1.0 if site % 2 == 0 else -1.0 for site in range(cfg.sites)], dtype=float)
    vacancy_charge = None
    if cfg.vacancy_site is not None and 0 <= int(cfg.vacancy_site) < cfg.sites:
        vacancy_charge = float(charges[int(cfg.vacancy_site)])
    return {
        "site_rows": site_rows,
        "nearest_neighbor_charge_correlation": nn_charge_corr,
        "nearest_neighbor_spin_correlation": nn_spin_corr,
        "global": {
            "total_charge": float(np.sum(charges)),
            "total_spin": float(np.sum(spins)),
            "mean_double_occupancy": float(np.mean(doubles)),
            "vacancy_charge": vacancy_charge,
            "staggered_charge": float(np.mean(parity * (charges - np.mean(charges)))),
            "staggered_spin": float(np.mean(parity * spins)),
            "mean_nn_charge_correlation": None if not nn_charge_corr else float(np.mean(nn_charge_corr)),
            "mean_nn_spin_correlation": None if not nn_spin_corr else float(np.mean(nn_spin_corr)),
        },
    }


def distribution_from_statevector(cfg: AdvantageScaleConfig) -> dict[str, float]:
    ideal_cfg = replace(cfg, measured=False)
    state = Statevector.from_instruction(build_main_circuit(ideal_cfg))
    return {
        format(index, f"0{cfg.qubits}b"): float(probability)
        for index, probability in enumerate(state.probabilities())
        if float(probability) > 1e-15
    }


def noiseless_observable_profile(
    cfg: AdvantageScaleConfig,
    cbit_to_mode: Mapping[int, Mapping[str, Any]],
    max_qubits: int,
) -> dict[str, Any] | None:
    if cfg.qubits > max_qubits:
        return None
    return observable_profile_from_counts(
        distribution_from_statevector(cfg),
        cfg,
        cbit_to_mode,
        readout_corrected=False,
    )


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _compute_reference_global(
    cfg: AdvantageScaleConfig,
    site_rows: list[dict[str, Any]],
    nn_charge: list[float] | None,
    nn_spin: list[float] | None,
) -> dict[str, float | None]:
    charges = np.asarray([row["charge"] for row in site_rows if row.get("charge") is not None], dtype=float)
    spins = np.asarray([row["spin"] for row in site_rows if row.get("spin") is not None], dtype=float)
    doubles = np.asarray(
        [row["double_occupancy"] for row in site_rows if row.get("double_occupancy") is not None],
        dtype=float,
    )
    parity = np.asarray([1.0 if site % 2 == 0 else -1.0 for site in range(cfg.sites)], dtype=float)
    charge_by_site = np.asarray([row.get("charge", np.nan) for row in site_rows], dtype=float)
    spin_by_site = np.asarray([row.get("spin", np.nan) for row in site_rows], dtype=float)
    vacancy_charge = None
    if cfg.vacancy_site is not None and 0 <= int(cfg.vacancy_site) < cfg.sites:
        value = site_rows[int(cfg.vacancy_site)].get("charge")
        vacancy_charge = None if value is None else float(value)
    return {
        "total_charge": None if len(charges) != cfg.sites else float(np.sum(charges)),
        "total_spin": None if len(spins) != cfg.sites else float(np.sum(spins)),
        "mean_double_occupancy": None if len(doubles) != cfg.sites else float(np.mean(doubles)),
        "vacancy_charge": vacancy_charge,
        "staggered_charge": None
        if np.isnan(charge_by_site).any()
        else float(np.mean(parity * (charge_by_site - np.mean(charge_by_site)))),
        "staggered_spin": None if np.isnan(spin_by_site).any() else float(np.mean(parity * spin_by_site)),
        "mean_nn_charge_correlation": None if not nn_charge else float(np.mean(nn_charge)),
        "mean_nn_spin_correlation": None if not nn_spin else float(np.mean(nn_spin)),
    }


def _normalize_reference_profile(raw: Mapping[str, Any], cfg: AdvantageScaleConfig) -> dict[str, Any]:
    site_rows_raw = raw.get("site_rows") or raw.get("sites") or raw.get("rows")
    if not isinstance(site_rows_raw, list):
        raise ValueError("Reference profile must contain a site_rows/sites/rows list")
    by_site: dict[int, dict[str, Any]] = {}
    for item in site_rows_raw:
        if not isinstance(item, Mapping):
            raise ValueError("Each reference site row must be an object")
        site = int(item["site"])
        n_up = _float_or_none(item.get("n_up"))
        n_down = _float_or_none(item.get("n_down"))
        charge = _float_or_none(item.get("charge"))
        spin = _float_or_none(item.get("spin"))
        if charge is None and n_up is not None and n_down is not None:
            charge = float(n_up + n_down)
        if spin is None and n_up is not None and n_down is not None:
            spin = float(n_up - n_down)
        if n_up is None and charge is not None and spin is not None:
            n_up = float(0.5 * (charge + spin))
        if n_down is None and charge is not None and spin is not None:
            n_down = float(0.5 * (charge - spin))
        by_site[site] = {
            "site": site,
            "n_up": n_up,
            "n_down": n_down,
            "charge": charge,
            "spin": spin,
            "double_occupancy": _float_or_none(item.get("double_occupancy")),
        }
    missing = [site for site in range(cfg.sites) if site not in by_site]
    if missing:
        raise ValueError(f"Reference profile is missing site rows: {missing}")
    site_rows = [by_site[site] for site in range(cfg.sites)]

    nn_charge = raw.get("nearest_neighbor_charge_correlation")
    nn_spin = raw.get("nearest_neighbor_spin_correlation")
    nn_charge_values = None
    nn_spin_values = None
    if isinstance(nn_charge, list):
        nn_charge_values = [_float_or_none(value) for value in nn_charge]
        nn_charge_values = None if any(value is None for value in nn_charge_values) else [float(value) for value in nn_charge_values]
    if isinstance(nn_spin, list):
        nn_spin_values = [_float_or_none(value) for value in nn_spin]
        nn_spin_values = None if any(value is None for value in nn_spin_values) else [float(value) for value in nn_spin_values]

    global_values = dict(raw.get("global", {})) if isinstance(raw.get("global"), Mapping) else {}
    computed_global = _compute_reference_global(cfg, site_rows, nn_charge_values, nn_spin_values)
    for key, value in computed_global.items():
        global_values.setdefault(key, value)
    return {
        "site_rows": site_rows,
        "nearest_neighbor_charge_correlation": nn_charge_values,
        "nearest_neighbor_spin_correlation": nn_spin_values,
        "global": global_values,
        "reference_source": raw.get("reference_source"),
        "reference_kind": raw.get("reference_kind"),
    }


def load_external_observable_reference(path: Path, cfg: AdvantageScaleConfig) -> dict[str, Any]:
    if path.suffix.lower() == ".json":
        raw = json.loads(path.read_text())
        if not isinstance(raw, Mapping):
            raise ValueError("JSON reference must be an object")
        if isinstance(raw.get("observable_profile"), Mapping):
            raw = raw["observable_profile"]
        elif isinstance(raw.get("noiseless_reference"), Mapping):
            raw = raw["noiseless_reference"]
        profile = _normalize_reference_profile(raw, cfg)
    else:
        rows = list(csv.DictReader(path.open()))
        if not rows:
            raise ValueError(f"Reference CSV has no rows: {path}")
        profile_names = {row.get("profile") for row in rows if row.get("profile")}
        if profile_names:
            preferred = "reference" if "reference" in profile_names else "noiseless" if "noiseless" in profile_names else sorted(profile_names)[0]
            rows = [row for row in rows if row.get("profile") == preferred]
        site_rows = []
        nn_charge: list[float | None] = []
        nn_spin: list[float | None] = []
        for row in rows:
            site_rows.append(
                {
                    "site": int(row["site"]),
                    "n_up": row.get("n_up"),
                    "n_down": row.get("n_down"),
                    "charge": row.get("charge"),
                    "spin": row.get("spin"),
                    "double_occupancy": row.get("double_occupancy"),
                }
            )
            if "nearest_neighbor_charge_correlation" in row and row.get("nearest_neighbor_charge_correlation") != "":
                nn_charge.append(_float_or_none(row.get("nearest_neighbor_charge_correlation")))
            if "nearest_neighbor_spin_correlation" in row and row.get("nearest_neighbor_spin_correlation") != "":
                nn_spin.append(_float_or_none(row.get("nearest_neighbor_spin_correlation")))
        raw = {
            "site_rows": site_rows,
            "nearest_neighbor_charge_correlation": nn_charge if nn_charge else None,
            "nearest_neighbor_spin_correlation": nn_spin if nn_spin else None,
            "reference_source": repo_relative_path(path),
            "reference_kind": "external_csv",
        }
        profile = _normalize_reference_profile(raw, cfg)
    profile["reference_source"] = repo_relative_path(path)
    return profile


def charge_density_from_local_rows(rows: list[dict[str, Any]], field: str, sites: int) -> list[float] | None:
    charge = np.zeros(sites, dtype=float)
    seen = np.zeros(sites, dtype=int)
    for row in rows:
        value = row.get(field)
        if value is None:
            return None
        site = int(row["site"])
        charge[site] += float(value)
        seen[site] += 1
    if any(count != 2 for count in seen):
        return None
    return [float(value) for value in charge]


def group_counts_with_metadata(
    raw_results: Mapping[str, Any],
    submitted_jobs: Mapping[str, Any],
    group_name: str,
    cfg: AdvantageScaleConfig,
) -> list[tuple[int, dict[str, Any], dict[str, int]]]:
    pubs = raw_results.get(group_name, {}).get("pubs", [])
    records = []
    for index, pub in enumerate(pubs):
        metadata, _ = group_metadata_for_pub(submitted_jobs, group_name, index)
        records.append((index, metadata, normalize_counts(pub["counts"], cfg.qubits)))
    return records


def nominal_main_counts(
    raw_results: Mapping[str, Any],
    submitted_jobs: Mapping[str, Any],
    cfg: AdvantageScaleConfig,
) -> dict[str, int]:
    records = group_counts_with_metadata(raw_results, submitted_jobs, "main", cfg)
    if not records:
        raise ValueError("No main result pubs found")
    for _, metadata, counts in records:
        if int(metadata.get("zne_noise_factor", 1) or 1) == 1:
            return counts
    return records[0][2]


def main_counts_by_zne_factor(
    raw_results: Mapping[str, Any],
    submitted_jobs: Mapping[str, Any],
    cfg: AdvantageScaleConfig,
) -> dict[int, dict[str, int]]:
    factors: dict[int, dict[str, int]] = {}
    for _, metadata, counts in group_counts_with_metadata(raw_results, submitted_jobs, "main", cfg):
        factor = int(metadata.get("zne_noise_factor", 1) or 1)
        factors[factor] = counts
    return dict(sorted(factors.items()))


def postselect_counts_by_mapping(
    counts: Mapping[str, int],
    cfg: AdvantageScaleConfig,
    cbit_to_mode: Mapping[int, Mapping[str, Any]],
) -> tuple[dict[str, int], dict[str, Any]]:
    target = expected_neel_particle_numbers(cfg.sites, cfg.vacancy_site)
    kept: dict[str, int] = {}
    total = 0
    kept_total = 0
    for bitstring, value in counts.items():
        count = int(value)
        total += count
        if particle_numbers_from_mapping(bitstring, cfg, cbit_to_mode) == target:
            kept[bitstring] = kept.get(bitstring, 0) + count
            kept_total += count
    return kept, {
        "target_n_up": target[0],
        "target_n_down": target[1],
        "kept_shots": kept_total,
        "total_shots": total,
        "discard_rate": None if total == 0 else float(1.0 - kept_total / total),
    }


def echo_counts_for_step(
    raw_results: Mapping[str, Any],
    submitted_jobs: Mapping[str, Any],
    cfg: AdvantageScaleConfig,
    *,
    echo_step: int,
    zne_noise_factor: int = 1,
) -> dict[str, int] | None:
    for _, metadata, counts in group_counts_with_metadata(raw_results, submitted_jobs, "echo", cfg):
        if metadata.get("echo_steps") == echo_step and int(metadata.get("zne_noise_factor", 1) or 1) == zne_noise_factor:
            return counts
    return None


def local_observable_rows(
    *,
    main_counts_data: Mapping[str, int],
    echo_counts_data: Mapping[str, int] | None,
    cfg: AdvantageScaleConfig,
    mapping: Mapping[str, Any],
    cbit_to_mode: Mapping[int, Mapping[str, Any]],
    p01: np.ndarray | None,
    p10: np.ndarray | None,
) -> list[dict[str, Any]]:
    initial_bits = initial_bits_from_mapping(mapping, cfg)
    confidence = float(cfg.mitigation.decay_confidence)
    rows: list[dict[str, Any]] = []
    for cbit in sorted(cbit_to_mode):
        mode = cbit_to_mode[cbit]
        initial_bit = int(initial_bits[cbit])
        echo_ideal_z = 1.0 if initial_bit == 0 else -1.0
        main_z_raw = z_expectation_from_counts(main_counts_data, cbit, cfg.qubits)
        main_z_readout = None
        if p01 is not None and p10 is not None:
            main_z_readout, _ = mitigated_z_expectation_from_counts(
                main_counts_data,
                qubits=[cbit],
                num_qubits=cfg.qubits,
                p01=p01,
                p10=p10,
            )

        echo_z_raw = None
        echo_z_readout = None
        if echo_counts_data is not None:
            echo_z_raw = z_expectation_from_counts(echo_counts_data, cbit, cfg.qubits)
            if p01 is not None and p10 is not None:
                echo_z_readout, _ = mitigated_z_expectation_from_counts(
                    echo_counts_data,
                    qubits=[cbit],
                    num_qubits=cfg.qubits,
                    p01=p01,
                    p10=p10,
                )

        echo_z_for_decay = echo_z_readout if echo_z_readout is not None else echo_z_raw
        main_z_for_decay = main_z_readout if main_z_readout is not None else main_z_raw
        damping = None
        denominator = None
        decay_recovered_z_unclipped = None
        decay_recovered_z = None
        decay_recovered_occupation = None
        if echo_z_for_decay is not None:
            damping = float(echo_z_for_decay / echo_ideal_z)
            denominator = float(confidence * damping + (1.0 - confidence))
            if abs(denominator) > 1e-9:
                decay_recovered_z_unclipped = float(main_z_for_decay / denominator)
                decay_recovered_z = float(np.clip(decay_recovered_z_unclipped, -1.0, 1.0))
                decay_recovered_occupation = float(0.5 * (1.0 - decay_recovered_z))

        rows.append(
            {
                "cbit": cbit,
                "site": int(mode["site"]),
                "spin": mode["spin"],
                "initial_bit": initial_bit,
                "echo_ideal_z": echo_ideal_z,
                "main_z_raw": main_z_raw,
                "main_occupation_raw": float(0.5 * (1.0 - main_z_raw)),
                "main_z_readout_corrected": main_z_readout,
                "main_occupation_readout_corrected": None
                if main_z_readout is None
                else float(0.5 * (1.0 - main_z_readout)),
                "echo_z_raw": echo_z_raw,
                "echo_z_readout_corrected": echo_z_readout,
                "decay_confidence": confidence,
                "decay_damping_factor": damping,
                "decay_denominator": denominator,
                "decay_recovered_z_unclipped": decay_recovered_z_unclipped,
                "decay_recovered_z": decay_recovered_z,
                "decay_recovered_occupation": decay_recovered_occupation,
            }
        )
    return rows


def write_local_observable_artifact(stage_dir: Path, rows: list[dict[str, Any]]) -> Path:
    csv_path = stage_dir / "ibm_staged_local_observables.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return csv_path


def charge_profiles_from_counts(
    *,
    counts: Mapping[str, int],
    echo_counts_data: Mapping[str, int] | None,
    cfg: AdvantageScaleConfig,
    mapping: Mapping[str, Any],
    cbit_to_mode: Mapping[int, Mapping[str, Any]],
    p01: np.ndarray | None,
    p10: np.ndarray | None,
) -> tuple[list[dict[str, Any]], dict[str, list[float] | None]]:
    rows = local_observable_rows(
        main_counts_data=counts,
        echo_counts_data=echo_counts_data,
        cfg=cfg,
        mapping=mapping,
        cbit_to_mode=cbit_to_mode,
        p01=p01,
        p10=p10,
    )
    return rows, {
        "raw": charge_density_from_local_rows(rows, "main_occupation_raw", cfg.sites),
        "readout_corrected": charge_density_from_local_rows(rows, "main_occupation_readout_corrected", cfg.sites),
        "readout_and_decay_recovered": charge_density_from_local_rows(rows, "decay_recovered_occupation", cfg.sites),
    }


def linear_zne_profile(factor_to_charge: Mapping[int, list[float] | None], sites: int) -> list[float] | None:
    usable = [(int(factor), charge) for factor, charge in factor_to_charge.items() if charge is not None]
    if len(usable) < 2:
        return None
    factors = np.asarray([factor for factor, _charge in usable], dtype=float)
    values = np.asarray([charge for _factor, charge in usable], dtype=float)
    extrapolated = []
    for site in range(sites):
        slope, intercept = np.polyfit(factors, values[:, site], deg=1)
        extrapolated.append(float(np.clip(intercept, 0.0, 2.0)))
    return extrapolated


def clip_observable_value(field: str, value: float) -> float:
    ranges = {
        "n_up": (0.0, 1.0),
        "n_down": (0.0, 1.0),
        "charge": (0.0, 2.0),
        "spin": (-1.0, 1.0),
        "double_occupancy": (0.0, 1.0),
        "total_charge": (0.0, float("inf")),
        "mean_double_occupancy": (0.0, 1.0),
    }
    lo, hi = ranges.get(field, (-float("inf"), float("inf")))
    return float(np.clip(value, lo, hi))


def linear_zne_observable_profile(
    factor_to_profile: Mapping[int, dict[str, Any] | None],
    cfg: AdvantageScaleConfig,
) -> dict[str, Any] | None:
    usable = [(int(factor), profile) for factor, profile in factor_to_profile.items() if profile is not None]
    if len(usable) < 2:
        return None
    factors = np.asarray([factor for factor, _profile in usable], dtype=float)
    if len(set(factors.tolist())) < 2:
        return None

    site_fields = ["n_up", "n_down", "charge", "spin", "double_occupancy"]
    site_rows: list[dict[str, float | int]] = []
    for site in range(cfg.sites):
        row: dict[str, float | int] = {"site": site}
        for field in site_fields:
            values = np.asarray([float(profile["site_rows"][site][field]) for _factor, profile in usable], dtype=float)
            _slope, intercept = np.polyfit(factors, values, deg=1)
            row[field] = clip_observable_value(field, float(intercept))
        site_rows.append(row)

    nn_charge: list[float] = []
    nn_spin: list[float] = []
    for site in range(cfg.sites - 1):
        values = np.asarray(
            [float(profile["nearest_neighbor_charge_correlation"][site]) for _factor, profile in usable],
            dtype=float,
        )
        _slope, intercept = np.polyfit(factors, values, deg=1)
        nn_charge.append(float(intercept))
        values = np.asarray(
            [float(profile["nearest_neighbor_spin_correlation"][site]) for _factor, profile in usable],
            dtype=float,
        )
        _slope, intercept = np.polyfit(factors, values, deg=1)
        nn_spin.append(float(intercept))

    charges = np.asarray([float(row["charge"]) for row in site_rows], dtype=float)
    spins = np.asarray([float(row["spin"]) for row in site_rows], dtype=float)
    doubles = np.asarray([float(row["double_occupancy"]) for row in site_rows], dtype=float)
    parity = np.asarray([1.0 if site % 2 == 0 else -1.0 for site in range(cfg.sites)], dtype=float)
    vacancy_charge = None
    if cfg.vacancy_site is not None and 0 <= int(cfg.vacancy_site) < cfg.sites:
        vacancy_charge = float(charges[int(cfg.vacancy_site)])
    return {
        "site_rows": site_rows,
        "nearest_neighbor_charge_correlation": nn_charge,
        "nearest_neighbor_spin_correlation": nn_spin,
        "global": {
            "total_charge": float(np.sum(charges)),
            "total_spin": float(np.sum(spins)),
            "mean_double_occupancy": float(np.mean(doubles)),
            "vacancy_charge": vacancy_charge,
            "staggered_charge": float(np.mean(parity * (charges - np.mean(charges)))),
            "staggered_spin": float(np.mean(parity * spins)),
            "mean_nn_charge_correlation": None if not nn_charge else float(np.mean(nn_charge)),
            "mean_nn_spin_correlation": None if not nn_spin else float(np.mean(nn_spin)),
        },
    }


def profile_site_values(profile: Mapping[str, Any] | None, field: str) -> list[float] | None:
    if profile is None:
        return None
    rows = profile.get("site_rows")
    if not isinstance(rows, list):
        return None
    values = []
    for row in rows:
        value = row.get(field)
        if value is None:
            return None
        values.append(float(value))
    return values


def profile_nn_values(profile: Mapping[str, Any] | None, field: str) -> list[float] | None:
    if profile is None:
        return None
    values = profile.get(field)
    if not isinstance(values, list):
        return None
    if any(value is None for value in values):
        return None
    return [float(value) for value in values]


def rmse_array(values: list[float] | None, reference: list[float] | None) -> float | None:
    if values is None or reference is None:
        return None
    arr = np.asarray(values, dtype=float)
    ref = np.asarray(reference, dtype=float)
    if arr.shape != ref.shape:
        return None
    return float(np.sqrt(np.mean((arr - ref) ** 2)))


def observable_route_rows(
    observable_profiles: Mapping[str, dict[str, Any] | None],
    ideal_profile: Mapping[str, Any] | None,
    cfg: AdvantageScaleConfig,
) -> list[dict[str, Any]]:
    ideal_n_up = profile_site_values(ideal_profile, "n_up")
    ideal_n_down = profile_site_values(ideal_profile, "n_down")
    ideal_charge = profile_site_values(ideal_profile, "charge")
    ideal_spin = profile_site_values(ideal_profile, "spin")
    ideal_double = profile_site_values(ideal_profile, "double_occupancy")
    ideal_nn_charge = profile_nn_values(ideal_profile, "nearest_neighbor_charge_correlation")
    ideal_nn_spin = profile_nn_values(ideal_profile, "nearest_neighbor_spin_correlation")
    ideal_global = {} if ideal_profile is None else dict(ideal_profile.get("global", {}))

    rows = []
    for name, profile in observable_profiles.items():
        if profile is None:
            continue
        global_values = dict(profile.get("global", {}))
        occupation_rmse = None
        n_up = profile_site_values(profile, "n_up")
        n_down = profile_site_values(profile, "n_down")
        if n_up is not None and n_down is not None and ideal_n_up is not None and ideal_n_down is not None:
            occupation_rmse = rmse_array(n_up + n_down, ideal_n_up + ideal_n_down)
        charge_rmse = rmse_array(profile_site_values(profile, "charge"), ideal_charge)
        spin_rmse = rmse_array(profile_site_values(profile, "spin"), ideal_spin)
        double_rmse = rmse_array(profile_site_values(profile, "double_occupancy"), ideal_double)
        nn_charge_rmse = rmse_array(
            profile_nn_values(profile, "nearest_neighbor_charge_correlation"),
            ideal_nn_charge,
        )
        nn_spin_rmse = rmse_array(
            profile_nn_values(profile, "nearest_neighbor_spin_correlation"),
            ideal_nn_spin,
        )
        total_charge_error = None
        total_spin_error = None
        mean_double_error = None
        if ideal_global:
            if global_values.get("total_charge") is not None and ideal_global.get("total_charge") is not None:
                total_charge_error = float(global_values["total_charge"] - ideal_global["total_charge"])
            if global_values.get("total_spin") is not None and ideal_global.get("total_spin") is not None:
                total_spin_error = float(global_values["total_spin"] - ideal_global["total_spin"])
            if (
                global_values.get("mean_double_occupancy") is not None
                and ideal_global.get("mean_double_occupancy") is not None
            ):
                mean_double_error = float(global_values["mean_double_occupancy"] - ideal_global["mean_double_occupancy"])

        components = [
            occupation_rmse,
            charge_rmse,
            spin_rmse,
            double_rmse,
            nn_charge_rmse,
            nn_spin_rmse,
            None if total_charge_error is None else abs(total_charge_error) / max(cfg.sites, 1),
            None if total_spin_error is None else abs(total_spin_error) / max(cfg.sites, 1),
        ]
        usable_components = [float(value) for value in components if value is not None]
        rows.append(
            {
                "profile": name,
                "observable_score_vs_noiseless": None
                if not usable_components
                else float(np.mean(usable_components)),
                "occupation_rmse": occupation_rmse,
                "charge_rmse": charge_rmse,
                "spin_rmse": spin_rmse,
                "double_occupancy_rmse": double_rmse,
                "nn_charge_corr_rmse": nn_charge_rmse,
                "nn_spin_corr_rmse": nn_spin_rmse,
                "total_charge": global_values.get("total_charge"),
                "total_charge_error": total_charge_error,
                "total_spin": global_values.get("total_spin"),
                "total_spin_error": total_spin_error,
                "mean_double_occupancy": global_values.get("mean_double_occupancy"),
                "mean_double_occupancy_error": mean_double_error,
                "vacancy_charge": global_values.get("vacancy_charge"),
                "staggered_charge": global_values.get("staggered_charge"),
                "staggered_spin": global_values.get("staggered_spin"),
                "mean_nn_charge_correlation": global_values.get("mean_nn_charge_correlation"),
                "mean_nn_spin_correlation": global_values.get("mean_nn_spin_correlation"),
            }
        )
    return sorted(
        rows,
        key=lambda row: float("inf")
        if row["observable_score_vs_noiseless"] is None
        else float(row["observable_score_vs_noiseless"]),
    )


def choose_headline_profile(
    profiles: Mapping[str, list[float] | None],
    ideal_charge: list[float] | None,
) -> tuple[str, list[float] | None, dict[str, float | None]]:
    rmses = {name: rmse(charge, ideal_charge) for name, charge in profiles.items()}
    if ideal_charge is not None:
        candidates = {
            name: value
            for name, value in rmses.items()
            if value is not None and name != "raw"
        }
        if candidates:
            best_name = min(candidates, key=lambda name: float(candidates[name]))
            return best_name, profiles.get(best_name), rmses
    preference = [
        "zne_symmetry_readout_corrected",
        "zne_readout_corrected",
        "symmetry_readout_corrected",
        "readout_corrected",
        "raw",
    ]
    for name in preference:
        if profiles.get(name) is not None:
            return name, profiles.get(name), rmses
    return "unavailable", None, rmses


def noiseless_charge_density(cfg: AdvantageScaleConfig, max_qubits: int) -> list[float] | None:
    if cfg.qubits > max_qubits:
        return None
    ideal_cfg = replace(cfg, measured=False)
    state = Statevector.from_instruction(build_main_circuit(ideal_cfg))
    mapping = semantic_mapping_manifest(cfg)
    cbit_to_mode = mode_by_classical_bit(mapping)
    probabilities = state.probabilities()
    charge = np.zeros(cfg.sites, dtype=float)
    for basis_index, probability in enumerate(probabilities):
        probability = float(probability)
        if probability <= 1e-15:
            continue
        bitstring = format(basis_index, f"0{cfg.qubits}b")
        for cbit, mode in cbit_to_mode.items():
            site = int(mode["site"])
            charge[site] += probability * bit_from_qiskit_bitstring(bitstring, cbit, cfg.qubits)
    return [float(value) for value in charge]


def rmse(values: list[float] | None, reference: list[float] | None) -> float | None:
    if values is None or reference is None:
        return None
    arr = np.asarray(values, dtype=float)
    ref = np.asarray(reference, dtype=float)
    return float(np.sqrt(np.mean((arr - ref) ** 2)))


def main_counts(raw_results: Mapping[str, Any], cfg: AdvantageScaleConfig) -> dict[str, int]:
    pubs = raw_results.get("main", {}).get("pubs", [])
    if not pubs:
        raise ValueError("No main result pubs found")
    return normalize_counts(pubs[0]["counts"], cfg.qubits)


def readout_params(raw_results: Mapping[str, Any], cfg: AdvantageScaleConfig) -> tuple[np.ndarray | None, np.ndarray | None, dict[str, Any] | None]:
    pubs = raw_results.get("readout", {}).get("pubs", [])
    if len(pubs) < 2:
        return None, None, None
    counts0 = normalize_counts(pubs[0]["counts"], cfg.qubits)
    counts1 = normalize_counts(pubs[1]["counts"], cfg.qubits)
    p01, p10, meta = estimate_local_readout_params(counts0, counts1, n_qubits=cfg.qubits)
    return p01, p10, meta


def robust_high_threshold(values: list[float], floor: float) -> float:
    if not values:
        return floor
    arr = np.asarray(values, dtype=float)
    median_value = float(np.median(arr))
    mad = float(np.median(np.abs(arr - median_value)))
    robust_sigma = 1.4826 * mad
    return float(max(floor, median_value + 4.0 * robust_sigma))


def readout_diagnostic_rows(
    *,
    cfg: AdvantageScaleConfig,
    mapping: Mapping[str, Any],
    layout: Mapping[str, Any],
    p01: np.ndarray | None,
    p10: np.ndarray | None,
    echo_data: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if p01 is None or p10 is None:
        return [], {
            "available": False,
            "reason": "readout calibration was not available",
            "suggested_avoid_physical_qubits": [],
        }

    initial_bits = initial_bits_from_mapping(mapping, cfg)
    cbit_to_mode = mode_by_classical_bit(mapping)
    logical_to_physical = layout.get("logical_to_physical", [])
    step0_rows = [
        row
        for row in echo_data
        if row.get("echo_steps") == 0 and int(row.get("zne_noise_factor", 1) or 1) == 1
    ]
    step0_flip_rates: dict[str, float] = {}
    if step0_rows:
        step0_flip_rates = dict(step0_rows[0].get("per_cbit_flip_rate", {}))

    p01_threshold = robust_high_threshold([float(value) for value in p01], 0.05)
    p10_threshold = robust_high_threshold([float(value) for value in p10], 0.05)
    step0_values = [float(value) for value in step0_flip_rates.values()]
    step0_threshold = robust_high_threshold(step0_values, 0.05)

    rows = []
    suggested_avoid = []
    for cbit in range(cfg.qubits):
        mode = cbit_to_mode.get(cbit, {})
        physical_qubit = None
        if isinstance(logical_to_physical, list) and cbit < len(logical_to_physical):
            physical_qubit = int(logical_to_physical[cbit])
        p01_value = float(p01[cbit])
        p10_value = float(p10[cbit])
        step0_flip = None
        if str(cbit) in step0_flip_rates:
            step0_flip = float(step0_flip_rates[str(cbit)])
        flags = []
        if p01_value >= p01_threshold:
            flags.append("high_p01")
        if p10_value >= p10_threshold:
            flags.append("high_p10")
        if step0_flip is not None and step0_flip >= step0_threshold:
            flags.append("high_step0_flip")
        if p01_value + p10_value >= 0.25:
            flags.append("near_singular_readout")
        if flags and physical_qubit is not None:
            suggested_avoid.append(physical_qubit)
        rows.append(
            {
                "cbit": cbit,
                "logical_qubit": int(mode.get("logical_qubit", cbit)),
                "physical_qubit": physical_qubit,
                "site": mode.get("site"),
                "spin": mode.get("spin"),
                "initial_bit": initial_bits[cbit],
                "p01_meas1_given_0": p01_value,
                "p10_meas0_given_1": p10_value,
                "assignment_error_sum": float(p01_value + p10_value),
                "assignment_error_max": float(max(p01_value, p10_value)),
                "step0_flip_rate": step0_flip,
                "flags": ";".join(flags),
                "suggest_avoid": bool(flags),
            }
        )

    return rows, {
        "available": True,
        "p01_threshold": p01_threshold,
        "p10_threshold": p10_threshold,
        "step0_flip_threshold": step0_threshold,
        "suggested_avoid_physical_qubits": sorted(dict.fromkeys(suggested_avoid)),
        "flagged_rows": [row for row in rows if row["suggest_avoid"]],
        "note": "Use suggested physical qubits with the runner --avoid-qubits option on the same backend.",
    }


def write_readout_diagnostic_artifact(stage_dir: Path, rows: list[dict[str, Any]]) -> Path | None:
    if not rows:
        return None
    csv_path = stage_dir / "ibm_staged_bad_qubits.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return csv_path


def write_charge_artifacts(
    stage_dir: Path,
    cfg: AdvantageScaleConfig,
    charge_profiles: Mapping[str, list[float] | None],
    headline_profile: str,
    ideal_charge: list[float] | None,
) -> tuple[Path, Path]:
    csv_path = stage_dir / "ibm_staged_charge_density.csv"
    raw_charge = charge_profiles["raw"]
    rows = []
    for site in range(cfg.sites):
        row = {"site": site}
        for name, charge in charge_profiles.items():
            row[f"{name}_charge"] = None if charge is None else charge[site]
            if ideal_charge is not None:
                row[f"{name}_minus_noiseless"] = None if charge is None else charge[site] - ideal_charge[site]
        row["headline_profile"] = headline_profile
        row["headline_charge"] = None if charge_profiles.get(headline_profile) is None else charge_profiles[headline_profile][site]
        row["noiseless_charge"] = None if ideal_charge is None else ideal_charge[site]
        rows.append(row)

    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    plot_path = stage_dir / "ibm_staged_charge_density.png"
    x = np.arange(cfg.sites)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    markers = {
        "raw": "o",
        "readout_corrected": "s",
        "symmetry_readout_corrected": "v",
        "zne_readout_corrected": "D",
        "zne_symmetry_readout_corrected": "P",
        "readout_and_decay_recovered": "^",
    }
    labels = {
        "raw": "IBM raw",
        "readout_corrected": "readout corrected",
        "symmetry_readout_corrected": "sector + readout",
        "zne_readout_corrected": "ZNE + readout",
        "zne_symmetry_readout_corrected": "ZNE + sector + readout",
        "readout_and_decay_recovered": "readout + decay recovery",
    }
    for name, charge in charge_profiles.items():
        if charge is None or name.startswith("symmetry_raw"):
            continue
        linewidth = 2.4 if name == headline_profile else 1.2
        ax.plot(x, charge, marker=markers.get(name, "."), linewidth=linewidth, label=labels.get(name, name))
    if ideal_charge is not None:
        ax.plot(x, ideal_charge, color="black", linewidth=1.5, label=f"noiseless {cfg.circuit_family}")
    ax.set_xlabel("site")
    ax.set_ylabel("<n_up+n_down>")
    ax.set_ylim(-0.05, 2.05)
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.set_title(f"IBM staged Fermi-Hubbard charge density, {cfg.qubits} qubits")
    fig.tight_layout()
    fig.savefig(plot_path, dpi=180)
    plt.close(fig)
    return csv_path, plot_path


def write_observable_suite_artifacts(
    stage_dir: Path,
    cfg: AdvantageScaleConfig,
    observable_profiles: Mapping[str, dict[str, Any] | None],
    route_rows: list[dict[str, Any]],
    ideal_profile: Mapping[str, Any] | None,
) -> tuple[Path, Path, Path]:
    suite_csv = stage_dir / "ibm_staged_observable_suite.csv"
    site_fields = [
        "profile",
        "site",
        "n_up",
        "n_down",
        "charge",
        "spin",
        "double_occupancy",
    ]
    with suite_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=site_fields, lineterminator="\n")
        writer.writeheader()
        for profile_name, profile in observable_profiles.items():
            if profile is None:
                continue
            for row in profile["site_rows"]:
                writer.writerow({"profile": profile_name, **{field: row.get(field) for field in site_fields if field != "profile"}})
        if ideal_profile is not None:
            for row in ideal_profile["site_rows"]:
                writer.writerow({"profile": "noiseless", **{field: row.get(field) for field in site_fields if field != "profile"}})

    route_csv = stage_dir / "ibm_staged_observable_route_scores.csv"
    with route_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(route_rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(route_rows)

    plot_path = stage_dir / "ibm_staged_observable_suite.png"
    preferred_profiles = [
        "raw",
        "readout_corrected",
        "zne_readout_corrected",
        "symmetry_readout_corrected",
        "zne_symmetry_readout_corrected",
    ]
    fig, axes = plt.subplots(3, 1, figsize=(8, 9), sharex=True)
    x = np.arange(cfg.sites)
    for profile_name in preferred_profiles:
        profile = observable_profiles.get(profile_name)
        if profile is None:
            continue
        rows = profile["site_rows"]
        label = profile_name.replace("_", " ")
        axes[0].plot(x, [row["charge"] for row in rows], marker="o", linewidth=1.2, label=label)
        axes[1].plot(x, [row["spin"] for row in rows], marker="s", linewidth=1.2, label=label)
        axes[2].plot(x, [row["double_occupancy"] for row in rows], marker="^", linewidth=1.2, label=label)
    if ideal_profile is not None:
        rows = ideal_profile["site_rows"]
        charge = profile_site_values(ideal_profile, "charge")
        spin = profile_site_values(ideal_profile, "spin")
        double = profile_site_values(ideal_profile, "double_occupancy")
        if charge is not None:
            axes[0].plot(x, charge, color="black", linewidth=1.6, label="reference")
        if spin is not None:
            axes[1].plot(x, spin, color="black", linewidth=1.6, label="reference")
        if double is not None:
            axes[2].plot(x, double, color="black", linewidth=1.6, label="reference")
    axes[0].set_ylabel("<n_up+n_down>")
    axes[1].set_ylabel("<n_up-n_down>")
    axes[2].set_ylabel("<n_up n_down>")
    axes[2].set_xlabel("site")
    axes[0].set_ylim(-0.05, 2.05)
    axes[1].set_ylim(-1.05, 1.05)
    axes[2].set_ylim(-0.05, 1.05)
    for ax in axes:
        ax.grid(True, alpha=0.3)
    axes[0].legend(loc="best", fontsize=8)
    fig.suptitle(f"IBM staged local observables, {cfg.qubits} qubits")
    fig.tight_layout()
    fig.savefig(plot_path, dpi=180)
    plt.close(fig)
    return suite_csv, route_csv, plot_path


def particle_numbers_from_mapping(
    bitstring: str,
    cfg: AdvantageScaleConfig,
    cbit_to_mode: Mapping[int, Mapping[str, Any]],
) -> tuple[int, int]:
    up_count = 0
    down_count = 0
    for cbit, mode in cbit_to_mode.items():
        bit = bit_from_qiskit_bitstring(bitstring, cbit, cfg.qubits)
        if mode.get("spin") == SPIN_UP:
            up_count += bit
        elif mode.get("spin") == SPIN_DOWN:
            down_count += bit
    return up_count, down_count


def sector_survival_parts(
    counts: Mapping[str, int],
    cfg: AdvantageScaleConfig,
    cbit_to_mode: Mapping[int, Mapping[str, Any]],
) -> dict[str, float]:
    target = expected_neel_particle_numbers(cfg.sites, cfg.vacancy_site)
    total = float(sum(counts.values()))
    if total <= 0.0:
        return {"n_up_survival": 0.0, "n_down_survival": 0.0, "sector_survival": 0.0}
    kept_up = 0
    kept_down = 0
    kept_total = 0
    for bitstring, value in counts.items():
        n_up, n_down = particle_numbers_from_mapping(bitstring, cfg, cbit_to_mode)
        if n_up == target[0]:
            kept_up += int(value)
        if n_down == target[1]:
            kept_down += int(value)
        if (n_up, n_down) == target:
            kept_total += int(value)
    return {
        "n_up_survival": float(kept_up / total),
        "n_down_survival": float(kept_down / total),
        "sector_survival": float(kept_total / total),
    }


def hamming_stats(counts: Mapping[str, int], initial_bitstring: str, n_qubits: int) -> dict[str, Any]:
    total = float(sum(counts.values()))
    if total <= 0.0:
        return {
            "mean_hamming_distance": 0.0,
            "mean_hamming_stderr": 0.0,
            "hamming_histogram": {},
            "per_cbit_flip_rate": {},
        }
    weighted = 0.0
    weighted_square = 0.0
    histogram: dict[str, int] = {}
    flips = np.zeros(n_qubits, dtype=float)
    for bitstring, value in counts.items():
        clean = clean_bitstring(bitstring, n_qubits)
        mismatches = [a != b for a, b in zip(clean, initial_bitstring)]
        hamming = sum(mismatches)
        normalized = hamming / n_qubits
        histogram[str(hamming)] = histogram.get(str(hamming), 0) + int(value)
        weighted += float(value) * normalized
        weighted_square += float(value) * normalized * normalized
        for display_index, mismatch in enumerate(mismatches):
            if mismatch:
                cbit = n_qubits - 1 - display_index
                flips[cbit] += float(value)
    mean = weighted / total
    variance = max(0.0, weighted_square / total - mean * mean)
    return {
        "mean_hamming_distance": float(mean),
        "mean_hamming_stderr": float(np.sqrt(variance / total)),
        "hamming_histogram": dict(sorted(histogram.items(), key=lambda item: int(item[0]))),
        "per_cbit_flip_rate": {str(index): float(flips[index] / total) for index in range(n_qubits)},
    }


def binomial_stderr(probability: float, shots: int) -> float:
    if shots <= 0:
        return 0.0
    p = min(max(float(probability), 0.0), 1.0)
    return float(np.sqrt(p * (1.0 - p) / shots))


def readout_limited_exact_return(
    initial_bits: list[int],
    p01: np.ndarray | None,
    p10: np.ndarray | None,
) -> float | None:
    if p01 is None or p10 is None:
        return None
    probability = 1.0
    for cbit, bit in enumerate(initial_bits):
        probability *= float(1.0 - p10[cbit] if bit else 1.0 - p01[cbit])
    return float(probability)


def load_submitted_jobs(stage_dir: Path) -> dict[str, Any]:
    path = stage_dir / "submitted_jobs.json"
    return json.loads(path.read_text()) if path.exists() else {}


def group_metadata_for_pub(
    submitted_jobs: Mapping[str, Any],
    group_name: str,
    index: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    group = submitted_jobs.get(group_name, {})
    metadata = group.get("circuit_metadata", []) if isinstance(group, dict) else []
    summaries = group.get("transpiled_summaries", []) if isinstance(group, dict) else []
    circuit_metadata = metadata[index] if index < len(metadata) and isinstance(metadata[index], dict) else {}
    transpiled_summary = summaries[index] if index < len(summaries) and isinstance(summaries[index], dict) else {}
    return circuit_metadata, transpiled_summary


def echo_rows(
    raw_results: Mapping[str, Any],
    cfg: AdvantageScaleConfig,
    echo_policy: str,
    explicit_steps: list[int] | None,
    mapping: Mapping[str, Any],
    submitted_jobs: Mapping[str, Any],
    p01: np.ndarray | None,
    p10: np.ndarray | None,
) -> list[dict[str, Any]]:
    pubs = raw_results.get("echo", {}).get("pubs", [])
    steps = explicit_steps if explicit_steps is not None else stage_echo_steps(cfg, echo_policy)
    if len(steps) != len(pubs):
        steps = list(steps[: len(pubs)]) + [None] * max(0, len(pubs) - len(steps))

    initial_bits = initial_bits_from_mapping(mapping, cfg)
    initial = initial_qiskit_key_from_mapping(mapping, cfg)
    cbit_to_mode = mode_by_classical_bit(mapping)
    readout_floor = readout_limited_exact_return(initial_bits, p01, p10)
    rows: list[dict[str, Any]] = []
    for index, pub in enumerate(pubs):
        counts = normalize_counts(pub["counts"], cfg.qubits)
        shots = int(sum(counts.values()))
        initial_count = int(counts.get(initial, 0))
        return_probability = float(initial_count / shots) if shots else 0.0
        sector_parts = sector_survival_parts(counts, cfg, cbit_to_mode)
        hamming = hamming_stats(counts, initial, cfg.qubits)
        circuit_metadata, transpiled_summary = group_metadata_for_pub(submitted_jobs, "echo", index)
        echo_step = circuit_metadata.get("echo_steps")
        if echo_step is None:
            echo_step = steps[index] if index < len(steps) else None
        zne_noise_factor = int(circuit_metadata.get("zne_noise_factor", 1) or 1)
        rows.append(
            {
                "echo_index": index,
                "echo_steps": echo_step,
                "zne_noise_factor": zne_noise_factor,
                "zne_fold_scope": circuit_metadata.get("zne_fold_scope"),
                "zne_extrapolator": circuit_metadata.get("zne_extrapolator"),
                "logical_forward_steps": circuit_metadata.get("logical_forward_steps"),
                "logical_inverse_steps": circuit_metadata.get("logical_inverse_steps"),
                "shots": shots,
                "initial_bitstring": initial,
                "initial_count": initial_count,
                "return_probability": return_probability,
                "return_probability_stderr": binomial_stderr(return_probability, shots),
                "readout_limited_return_probability": readout_floor,
                "n_up_survival": sector_parts["n_up_survival"],
                "n_down_survival": sector_parts["n_down_survival"],
                "sector_survival": sector_parts["sector_survival"],
                "sector_survival_stderr": binomial_stderr(sector_parts["sector_survival"], shots),
                "mean_hamming_distance": hamming["mean_hamming_distance"],
                "mean_hamming_stderr": hamming["mean_hamming_stderr"],
                "hamming_histogram": hamming["hamming_histogram"],
                "per_cbit_flip_rate": hamming["per_cbit_flip_rate"],
                "transpiled_depth": transpiled_summary.get("depth"),
                "transpiled_two_qubit_depth": transpiled_summary.get("two_qubit_depth"),
                "transpiled_two_qubit_count": transpiled_summary.get("two_qubit_count"),
                "transpiled_cz_count": transpiled_summary.get("operation_counts", {}).get("cz")
                if isinstance(transpiled_summary.get("operation_counts"), dict)
                else None,
                "transpiled_summary": transpiled_summary,
                "circuit_metadata": circuit_metadata,
                "unique_bitstrings": len(counts),
            }
        )
    step0_by_factor = {
        int(row.get("zne_noise_factor", 1)): float(row["return_probability"])
        for row in rows
        if row.get("echo_steps") == 0
    }
    for row in rows:
        step0_return = step0_by_factor.get(int(row.get("zne_noise_factor", 1)))
        row["return_probability_step0"] = step0_return
        row["return_probability_normalized_by_step0"] = (
            None if step0_return is None or step0_return <= 0.0 else float(row["return_probability"]) / step0_return
        )
        cz_count = row.get("transpiled_cz_count")
        normalized = row["return_probability_normalized_by_step0"]
        row["echo_decay_per_cz"] = (
            None
            if cz_count in {None, 0} or normalized is None or normalized <= 0.0
            else float(-np.log(normalized) / float(cz_count))
        )
    return rows


def linear_zero_noise(values: list[tuple[float, float]]) -> tuple[float, float]:
    if len(values) < 2:
        raise ValueError("ZNE needs at least two noise factors")
    x = np.asarray([item[0] for item in values], dtype=float)
    y = np.asarray([item[1] for item in values], dtype=float)
    if len(set(x.tolist())) < 2:
        raise ValueError("ZNE noise factors must not all be equal")
    slope, intercept = np.polyfit(x, y, deg=1)
    return float(intercept), float(slope)


def zne_echo_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[Any, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row.get("echo_steps"), []).append(row)

    zne_rows: list[dict[str, Any]] = []
    for echo_step, step_rows in sorted(grouped.items(), key=lambda item: (-1 if item[0] is None else int(item[0]))):
        by_factor = {
            int(row.get("zne_noise_factor", 1)): row
            for row in step_rows
            if row.get("zne_noise_factor") is not None
        }
        if len(by_factor) < 2:
            continue
        factors = sorted(by_factor)
        return_unclipped, return_slope = linear_zero_noise(
            [(factor, float(by_factor[factor]["return_probability"])) for factor in factors]
        )
        sector_unclipped, sector_slope = linear_zero_noise(
            [(factor, float(by_factor[factor]["sector_survival"])) for factor in factors]
        )
        hamming_unclipped, hamming_slope = linear_zero_noise(
            [(factor, float(by_factor[factor]["mean_hamming_distance"])) for factor in factors]
        )
        zne_rows.append(
            {
                "echo_steps": echo_step,
                "zne_noise_factors": factors,
                "zne_extrapolator": "linear",
                "return_probability_zne_linear_unclipped": return_unclipped,
                "return_probability_zne_linear": float(np.clip(return_unclipped, 0.0, 1.0)),
                "return_probability_zne_linear_slope": return_slope,
                "sector_survival_zne_linear_unclipped": sector_unclipped,
                "sector_survival_zne_linear": float(np.clip(sector_unclipped, 0.0, 1.0)),
                "sector_survival_zne_linear_slope": sector_slope,
                "mean_hamming_zne_linear_unclipped": hamming_unclipped,
                "mean_hamming_zne_linear": float(np.clip(hamming_unclipped, 0.0, 1.0)),
                "mean_hamming_zne_linear_slope": hamming_slope,
                "nominal_return_probability": float(by_factor[min(factors)]["return_probability"]),
                "nominal_sector_survival": float(by_factor[min(factors)]["sector_survival"]),
                "nominal_mean_hamming": float(by_factor[min(factors)]["mean_hamming_distance"]),
            }
        )

    step0 = next((row for row in zne_rows if row.get("echo_steps") == 0), None)
    step0_return = None if step0 is None else float(step0["return_probability_zne_linear"])
    for row in zne_rows:
        row["return_probability_zne_linear_step0"] = step0_return
        row["return_probability_zne_linear_normalized_by_step0"] = (
            None
            if step0_return is None or step0_return <= 0.0
            else float(row["return_probability_zne_linear"]) / step0_return
        )
    return zne_rows


def write_echo_artifacts(stage_dir: Path, rows: list[dict[str, Any]]) -> tuple[Path | None, Path | None]:
    if not rows:
        return None, None

    csv_path = stage_dir / "ibm_staged_echo_depths.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    plot_path = stage_dir / "ibm_staged_echo_depths.png"
    fig, ax = plt.subplots(figsize=(7, 4.2))
    factors = sorted({int(row.get("zne_noise_factor", 1)) for row in rows})
    for factor in factors:
        factor_rows = [row for row in rows if int(row.get("zne_noise_factor", 1)) == factor]
        x = [row["echo_index"] if row["echo_steps"] is None else row["echo_steps"] for row in factor_rows]
        ax.errorbar(
            x,
            [row["return_probability"] for row in factor_rows],
            yerr=[row["return_probability_stderr"] for row in factor_rows],
            marker="o",
            label=f"exact return raw, zne f={factor}",
        )
        if any(row["return_probability_normalized_by_step0"] is not None for row in factor_rows):
            ax.plot(
                x,
                [
                    np.nan
                    if row["return_probability_normalized_by_step0"] is None
                    else row["return_probability_normalized_by_step0"]
                    for row in factor_rows
                ],
                marker="d",
                linestyle="--",
                label=f"return / step-0, zne f={factor}",
            )
    nominal_rows = [row for row in rows if int(row.get("zne_noise_factor", 1)) == min(factors)]
    x_nominal = [row["echo_index"] if row["echo_steps"] is None else row["echo_steps"] for row in nominal_rows]
    ax.plot(x_nominal, [row["sector_survival"] for row in nominal_rows], marker="s", label="N_up/N_down sector, nominal")
    ax.plot(x_nominal, [row["mean_hamming_distance"] for row in nominal_rows], marker="^", label="mean Hamming / qubit, nominal")
    ax.set_xlabel("echo Trotter steps")
    ax.set_ylabel("probability / normalized distance")
    ax.set_ylim(-0.03, 1.03)
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.set_title("Echo-depth characterization")
    fig.tight_layout()
    fig.savefig(plot_path, dpi=180)
    plt.close(fig)
    return csv_path, plot_path


def write_zne_echo_artifacts(stage_dir: Path, rows: list[dict[str, Any]]) -> tuple[Path | None, Path | None]:
    if not rows:
        return None, None

    csv_path = stage_dir / "ibm_staged_echo_zne.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    plot_path = stage_dir / "ibm_staged_echo_zne.png"
    x = [row["echo_steps"] for row in rows]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(x, [row["nominal_return_probability"] for row in rows], marker="o", label="nominal exact return")
    ax.plot(
        x,
        [row["return_probability_zne_linear"] for row in rows],
        marker="d",
        label="ZNE linear exact return",
    )
    ax.plot(x, [row["sector_survival_zne_linear"] for row in rows], marker="s", label="ZNE sector survival")
    ax.plot(x, [row["mean_hamming_zne_linear"] for row in rows], marker="^", label="ZNE mean Hamming / qubit")
    ax.set_xlabel("echo Trotter steps")
    ax.set_ylabel("probability / normalized distance")
    ax.set_ylim(-0.03, 1.03)
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.set_title("Echo ZNE linear extrapolation")
    fig.tight_layout()
    fig.savefig(plot_path, dpi=180)
    plt.close(fig)
    return csv_path, plot_path


def compact_job_summary(raw_results: Mapping[str, Any]) -> dict[str, Any]:
    summary = {}
    for group_name, record in raw_results.items():
        summary[group_name] = {
            "job_id": record.get("job_id"),
            "backend": record.get("backend"),
            "status": record.get("status"),
            "pub_count": len(record.get("pubs", [])),
            "shots": [pub.get("shots") for pub in record.get("pubs", [])],
        }
    return summary


def write_summary(
    stage_dir: Path,
    cfg: AdvantageScaleConfig,
    plan: Mapping[str, Any],
    mapping: Mapping[str, Any],
    raw_results: Mapping[str, Any],
    readout_meta: Mapping[str, Any] | None,
    charge_profiles: Mapping[str, list[float] | None],
    charge_profile_rmses: Mapping[str, float | None],
    headline_profile: str,
    symmetry_postselection: Mapping[str, Any],
    zne_charge_metadata: Mapping[str, Any],
    local_observable_rows_data: list[dict[str, Any]],
    observable_profiles: Mapping[str, dict[str, Any] | None],
    observable_route_rows_data: list[dict[str, Any]],
    ideal_observable_profile: Mapping[str, Any] | None,
    readout_diagnostics: Mapping[str, Any],
    echo_data: list[dict[str, Any]],
    echo_zne_data: list[dict[str, Any]],
    artifacts: Mapping[str, str | None],
    max_noiseless_qubits: int,
) -> tuple[Path, Path]:
    summary_path = stage_dir / "ibm_staged_summary.json"
    md_path = stage_dir / "ibm_staged_summary.md"
    layout = plan.get("layout_selection", {})
    compile_selection = plan.get("compile_selection", {})
    selected_groups = compile_selection.get("selected_groups", {}) if isinstance(compile_selection, dict) else {}
    main_compile = selected_groups.get("main", {}) if isinstance(selected_groups, dict) else {}
    echo_compile = selected_groups.get("echo", {}) if isinstance(selected_groups, dict) else {}

    raw_rmse = charge_profile_rmses.get("raw")
    corrected_rmse = charge_profile_rmses.get("readout_corrected")
    decay_recovered_rmse = charge_profile_rmses.get("readout_and_decay_recovered")
    decay_recovered_charge = charge_profiles.get("readout_and_decay_recovered")
    headline_charge = charge_profiles.get(headline_profile)
    scored_observable_route_rows = [
        row
        for row in observable_route_rows_data
        if row.get("observable_score_vs_noiseless") is not None
    ]
    best_observable_route = scored_observable_route_rows[0] if scored_observable_route_rows else None
    nominal_symmetry = symmetry_postselection.get("nominal") if isinstance(symmetry_postselection, Mapping) else None
    symmetry_discard_rate = None
    if isinstance(nominal_symmetry, Mapping) and nominal_symmetry.get("discard_rate") is not None:
        symmetry_discard_rate = float(nominal_symmetry["discard_rate"])
    symmetry_diagnostic_only = symmetry_discard_rate is not None and symmetry_discard_rate > 0.5
    recommended_observable_route = next(
        (
            row
            for row in scored_observable_route_rows
            if not (symmetry_diagnostic_only and "symmetry" in str(row.get("profile", "")))
            and not str(row.get("profile", "")).startswith("frontier_soft_sector")
        ),
        best_observable_route,
    )
    final_echo = echo_data[-1] if echo_data else None
    effective_echo_steps = [row["echo_steps"] for row in echo_data]
    warnings = []
    if mapping.get("mapping_source") == "derived_from_config_for_legacy_stage_plan":
        warnings.append(str(mapping.get("warning")))
    step0 = next((row for row in echo_data if row.get("echo_steps") == 0), None)
    if step0 is None:
        warnings.append("No echo_step=0 was available, so exact return is not SPAM-normalized.")
    elif float(step0["return_probability"]) < 0.5:
        warnings.append(
            "echo_step=0 exact return is low; check bitstring mapping, state preparation, readout, and layout before interpreting depth decay."
        )
    if not plan.get("semantic_mapping"):
        warnings.append("Physical charge-density labels rely on scaffold-derived mapping because this is a legacy stage plan.")
    if mapping.get("mode_order_warning"):
        warnings.append(str(mapping["mode_order_warning"]))
    if cfg.circuit_family == "native-fswap-cz-skeleton":
        warnings.append(
            "native-fswap-cz-skeleton is a resource/depth skeleton, not a validated Fermi-Hubbard Hamiltonian implementation."
        )
    if cfg.circuit_family == "native-fswap-cz":
        warnings.append(
            "native-fswap-cz uses the physical fSWAP/hopping builder; local observables still need hardware-noise validation."
        )
    if any(row.get("logical_forward_steps") is None for row in echo_data):
        warnings.append("Echo circuit metadata is missing for at least one PUB; logical forward/inverse depth is not claimed for that legacy result.")
        warnings.append("This is a local-observable hardware diagnostic, not a validation of physical Hubbard dynamics or quantum advantage.")
    if ideal_observable_profile is None:
        warnings.append(
            f"No noiseless exact reference was generated because this stage has {cfg.qubits} qubits; RMSE route ranking is unavailable until a tensor-network or smaller exact reference is supplied."
        )
    warnings.append("Exact return is raw and includes SPAM/readout; it is retained as an echo diagnostic, not the headline physics metric.")
    if decay_recovered_charge is None:
        warnings.append("Decay recovery was not available because no matching final-depth echo local-Z data was found.")
    elif corrected_rmse is not None and decay_recovered_rmse is not None and decay_recovered_rmse > corrected_rmse:
        warnings.append(
            "Echo-local-Z decay recovery worsened RMSE against the available noiseless reference; it is kept as a diagnostic, not selected blindly."
        )
    if cfg.mitigation.zne_mitigation:
        warnings.append(
            "ZNE is client-side global circuit folding over Sampler counts; extrapolated exact return is a diagnostic, not a fidelity proof."
        )
    elif charge_profiles.get("zne_readout_corrected") is None:
        warnings.append("No charge-density ZNE profile is available because this stage has only the nominal noise factor.")
    if symmetry_discard_rate is not None:
        if symmetry_discard_rate > 0.5:
            warnings.append(
                f"Symmetry postselection discards {symmetry_discard_rate:.3f} of nominal shots; treat sector-filtered observables as diagnostic."
            )
    frontier_profiles = [
        name
        for name, profile in observable_profiles.items()
        if profile is not None and name.startswith("frontier_soft_sector")
    ]
    if frontier_profiles:
        warnings.append(
            "Frontier soft-sector profiles are opt-in diagnostics; they are excluded from headline and recommended-route selection by default."
        )
    damping_values = [
        float(row["decay_damping_factor"])
        for row in local_observable_rows_data
        if row.get("decay_damping_factor") is not None
    ]
    damping_summary = None
    if damping_values:
        damping_summary = {
            "min": float(np.min(damping_values)),
            "median": float(np.median(damping_values)),
            "max": float(np.max(damping_values)),
        }
    reference_source = None if ideal_observable_profile is None else display_reference_source(
        ideal_observable_profile.get("reference_source", "internal_statevector")
    )
    summary = {
        "run_dir": repo_relative_path(stage_dir),
        "config": asdict(cfg),
        "echo_policy": plan.get("echo_policy"),
        "echo_steps": effective_echo_steps,
        "echo_convention": plan.get("echo_convention", "legacy stage plan; convention inferred from submitted circuit order"),
        "semantic_mapping": mapping,
        "warnings": warnings,
        "jobs": compact_job_summary(raw_results),
        "layout_selection": layout,
        "compile_excerpt": {
            "enabled": compile_selection.get("enabled") if isinstance(compile_selection, dict) else None,
            "selected_layout_rank": compile_selection.get("selected_layout", {}).get("rank")
            if isinstance(compile_selection, dict) and isinstance(compile_selection.get("selected_layout"), dict)
            else None,
            "main_cz_count": main_compile.get("score_terms", {}).get("cz_count") if isinstance(main_compile, dict) else None,
            "main_two_qubit_count": main_compile.get("score_terms", {}).get("two_qubit_count") if isinstance(main_compile, dict) else None,
            "main_two_qubit_depth": main_compile.get("score_terms", {}).get("two_qubit_depth_max") if isinstance(main_compile, dict) else None,
            "main_depth": main_compile.get("score_terms", {}).get("depth_max") if isinstance(main_compile, dict) else None,
            "echo_cz_count": echo_compile.get("score_terms", {}).get("cz_count") if isinstance(echo_compile, dict) else None,
            "echo_two_qubit_count": echo_compile.get("score_terms", {}).get("two_qubit_count") if isinstance(echo_compile, dict) else None,
            "echo_two_qubit_depth": echo_compile.get("score_terms", {}).get("two_qubit_depth_max") if isinstance(echo_compile, dict) else None,
            "echo_depth": echo_compile.get("score_terms", {}).get("depth_max") if isinstance(echo_compile, dict) else None,
        },
        "readout_calibration": readout_meta,
        "charge_rmse_vs_noiseless": {
            "raw": raw_rmse,
            "readout_corrected": corrected_rmse,
            "readout_and_decay_recovered": decay_recovered_rmse,
            "profiles": dict(charge_profile_rmses),
            "headline_profile": headline_profile,
            "headline": charge_profile_rmses.get(headline_profile),
            "noiseless_reference_max_qubits": max_noiseless_qubits,
            "reference_source": reference_source,
        },
        "mitigation_outputs": {
            "runtime_dynamical_decoupling": {
                "enabled": cfg.mitigation.dynamical_decoupling,
                "sequence": cfg.mitigation.dd_sequence,
                "scheduling_method": cfg.mitigation.dd_scheduling_method,
            },
            "runtime_pauli_twirling": {
                "enabled": cfg.mitigation.pauli_twirling,
                "randomizations": cfg.mitigation.twirl_randomizations,
                "strategy": cfg.mitigation.twirl_strategy,
            },
            "readout_correction": {
                "enabled": cfg.mitigation.readout_correction,
                "available": readout_meta is not None,
            },
            "decay_recovery": {
                "enabled": cfg.mitigation.decay_recovery,
                "available": decay_recovered_charge is not None,
                "confidence": cfg.mitigation.decay_confidence,
            },
            "symmetry_postselection": symmetry_postselection,
            "zero_noise_extrapolation": zne_charge_metadata,
            "available_charge_profiles": sorted(name for name, value in charge_profiles.items() if value is not None),
        },
        "local_observables": {
            "headline_metric": f"site charge density using `{headline_profile}`",
            "headline_charge": headline_charge,
            "charge_profiles": dict(charge_profiles),
            "decay_recovery_confidence": cfg.mitigation.decay_confidence,
            "decay_recovery_echo_step": cfg.steps,
            "decay_recovery_zne_noise_factor": 1,
            "decay_damping_summary": damping_summary,
            "rows": local_observable_rows_data,
        },
        "observable_suite": {
            "profiles": {
                name: profile
                for name, profile in observable_profiles.items()
                if profile is not None
            },
            "noiseless_reference": ideal_observable_profile,
            "reference_source": reference_source,
            "route_scores": observable_route_rows_data,
            "best_route": best_observable_route,
            "recommended_route": recommended_observable_route,
            "symmetry_diagnostic_only": symmetry_diagnostic_only,
        },
        "readout_diagnostics": dict(readout_diagnostics),
        "echo_depths": echo_data,
        "echo_zne": echo_zne_data,
        "final_echo_return_probability": None if final_echo is None else final_echo["return_probability"],
        "artifacts": artifacts,
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    lines = [
        "# IBM staged Fermi-Hubbard summary",
        "",
        f"- run directory: `{repo_relative_path(stage_dir)}`",
        f"- backend: `{raw_results.get('main', {}).get('backend')}`",
        f"- qubits/sites: {cfg.qubits}/{cfg.sites}",
        f"- steps/dt/time: {cfg.steps}/{cfg.dt:g}/{cfg.total_time:g}",
        f"- circuit family: `{cfg.circuit_family}`",
        f"- echo policy: `{plan.get('echo_policy')}`",
        f"- echo steps analyzed: {effective_echo_steps}",
        f"- ZNE enabled/stage noise factors: {cfg.mitigation.zne_mitigation} / {zne_charge_metadata.get('noise_factors')}",
        f"- runtime DD: {cfg.mitigation.dynamical_decoupling} ({cfg.mitigation.dd_sequence}, {cfg.mitigation.dd_scheduling_method})",
        f"- runtime twirling: {cfg.mitigation.pauli_twirling} ({cfg.mitigation.twirl_randomizations}, {cfg.mitigation.twirl_strategy})",
        f"- headline charge profile: `{headline_profile}`",
        f"- observable reference source: `{reference_source}`",
        f"- initial Qiskit counts key: `{mapping.get('initial_qiskit_counts_key')}`",
        "",
        "## Quality controls",
        "",
        f"- layout score: {layout.get('score')}",
        f"- selected readout error mean/max: {layout.get('selected_readout_error_mean')} / {layout.get('selected_readout_error_max')}",
        f"- selected CZ error mean/max: {layout.get('selected_cz_error_mean')} / {layout.get('selected_cz_error_max')}",
        f"- main CZ/two-qubit-depth/depth after transpile: {summary['compile_excerpt']['main_cz_count']} / {summary['compile_excerpt']['main_two_qubit_depth']} / {summary['compile_excerpt']['main_depth']}",
        f"- echo CZ/two-qubit-depth/depth after transpile: {summary['compile_excerpt']['echo_cz_count']} / {summary['compile_excerpt']['echo_two_qubit_depth']} / {summary['compile_excerpt']['echo_depth']}",
        "",
        "## Readout and charge",
        "",
        f"- readout p01 mean/max: {None if readout_meta is None else readout_meta.get('p01_mean')} / {None if readout_meta is None else readout_meta.get('p01_max')}",
        f"- readout p10 mean/max: {None if readout_meta is None else readout_meta.get('p10_mean')} / {None if readout_meta is None else readout_meta.get('p10_max')}",
        f"- charge RMSE raw vs noiseless: {raw_rmse}",
        f"- charge RMSE readout-corrected vs noiseless: {corrected_rmse}",
        f"- charge RMSE sector+readout vs noiseless: {charge_profile_rmses.get('symmetry_readout_corrected')}",
        f"- charge RMSE ZNE+readout vs noiseless: {charge_profile_rmses.get('zne_readout_corrected')}",
        f"- charge RMSE ZNE+sector+readout vs noiseless: {charge_profile_rmses.get('zne_symmetry_readout_corrected')}",
        f"- charge RMSE readout + decay recovery vs noiseless: {decay_recovered_rmse}",
        f"- charge RMSE headline vs noiseless: {charge_profile_rmses.get(headline_profile)}",
        f"- best numerical multi-observable route: {None if best_observable_route is None else best_observable_route.get('profile')} / score {None if best_observable_route is None else best_observable_route.get('observable_score_vs_noiseless')}",
        f"- recommended multi-observable route: {None if recommended_observable_route is None else recommended_observable_route.get('profile')} / score {None if recommended_observable_route is None else recommended_observable_route.get('observable_score_vs_noiseless')}",
        f"- suggested bad-qubit avoid list: {readout_diagnostics.get('suggested_avoid_physical_qubits')}",
        f"- local-Z decay damping min/median/max: {None if damping_summary is None else (damping_summary['min'], damping_summary['median'], damping_summary['max'])}",
        f"- symmetry postselection nominal kept/discard: {None if nominal_symmetry is None else nominal_symmetry.get('kept_shots')} / {None if nominal_symmetry is None else nominal_symmetry.get('discard_rate')}",
        f"- charge ZNE available profiles: {zne_charge_metadata.get('available_profiles')}",
        "",
        "## Paper-style local observable headline",
        "",
        "Headline physics output is the local charge-density observable. Exact echo return is retained below as a hardware diagnostic.",
        "",
    ]
    table_profiles = []
    for name in [
        "raw",
        "readout_corrected",
        "symmetry_readout_corrected",
        "zne_readout_corrected",
        "zne_symmetry_readout_corrected",
        "readout_and_decay_recovered",
        headline_profile,
    ]:
        if name not in table_profiles and charge_profiles.get(name) is not None:
            table_profiles.append(name)
    for name in charge_profiles:
        if name.startswith("frontier_soft_sector") and name not in table_profiles and charge_profiles.get(name) is not None:
            table_profiles.append(name)
    if table_profiles:
        header = "| site | " + " | ".join(table_profiles) + " |"
        separator = "|---:|" + "|".join("---:" for _ in table_profiles) + "|"
        lines.extend([header, separator])
        for site in range(cfg.sites):
            values = " | ".join(f"{charge_profiles[name][site]:.6f}" for name in table_profiles if charge_profiles.get(name) is not None)
            lines.append(f"| {site} | {values} |")
        lines.append("")

    zne_readout_rmse = charge_profile_rmses.get("zne_readout_corrected")
    zne_improves_charge = (
        corrected_rmse is not None
        and zne_readout_rmse is not None
        and float(zne_readout_rmse) < float(corrected_rmse)
    )
    decay_improves_charge = (
        corrected_rmse is not None
        and decay_recovered_rmse is not None
        and float(decay_recovered_rmse) < float(corrected_rmse)
    )
    symmetry_discard_text = None
    if symmetry_discard_rate is not None:
        symmetry_discard_text = f"{100.0 * symmetry_discard_rate:.1f}%"

    lines.extend(
        [
            "## Multi-Observable Analysis",
            "",
            f"This section reuses the same {cfg.qubits}-qubit hardware counts; no extra hardware time is used for these derived diagnostics.",
            "",
            "Additional diagonal observables in this summary:",
            "",
            "- charge density",
            "- spin density",
            "- double occupancy",
            "- nearest-neighbor charge correlations",
            "- nearest-neighbor spin correlations",
            "- total charge / total spin",
            "- multi-observable route score per mitigation profile",
            "",
            "Derived artifacts:",
            "",
            f"- observable suite CSV: `{artifacts.get('observable_suite_csv')}`",
            f"- route scores CSV: `{artifacts.get('observable_route_scores_csv')}`",
            f"- observable suite plot: `{artifacts.get('observable_suite_plot')}`",
            f"- updated summary: `{repo_relative_path(md_path)}`",
            "",
            "Route verdict for this run:",
            "",
            f"- best numerical score: `{None if best_observable_route is None else best_observable_route.get('profile')}`, score {None if best_observable_route is None else best_observable_route.get('observable_score_vs_noiseless')}",
            f"- recommended route: `{None if recommended_observable_route is None else recommended_observable_route.get('profile')}`, score {None if recommended_observable_route is None else recommended_observable_route.get('observable_score_vs_noiseless')}",
            f"- RMSE reference available: {ideal_observable_profile is not None}",
            f"- symmetry postselection discard: {symmetry_discard_text}",
            f"- symmetry profile status: {'diagnostic-only' if symmetry_diagnostic_only else 'eligible as headline candidate'}",
            f"- ZNE improves charge RMSE versus readout-corrected: {zne_improves_charge}",
            f"- echo-local-Z decay recovery improves charge RMSE versus readout-corrected: {decay_improves_charge}",
            "",
            "Interpretation: the robust noise strategy is to compare mitigation routes per observable, not to blindly stack every mitigation method. Symmetry-filtered profiles are useful diagnostics when the discard rate is high, while the recommended route excludes them from the headline in that case.",
            "",
        ]
    )

    lines.extend(
        [
            "## Observable Route Ranking",
            "",
            "Ranking uses spin-orbital occupation RMSE, charge density, spin density, double occupancy, nearest-neighbor charge/spin correlations, total charge, and total spin against the available reference.",
            "Profiles using symmetry postselection are diagnostic-only when the discard rate is above 50%.",
            "",
        ]
    )
    if observable_route_rows_data:
        lines.extend(
            [
                "| profile | score | occupation RMSE | charge RMSE | spin RMSE | double RMSE | total charge err | total spin err | vacancy charge |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for row in observable_route_rows_data:
            lines.append(
                f"| {row['profile']} | {row['observable_score_vs_noiseless']} | "
                f"{row['occupation_rmse']} | {row['charge_rmse']} | {row['spin_rmse']} | {row['double_occupancy_rmse']} | "
                f"{row['total_charge_error']} | {row['total_spin_error']} | {row['vacancy_charge']} |"
            )
    else:
        lines.append("No observable route ranking was available.")
    lines.append("")

    if readout_diagnostics.get("available"):
        lines.extend(
            [
                "## Bad-Qubit Diagnostic",
                "",
                f"- suggested physical avoid list: `{','.join(str(q) for q in readout_diagnostics.get('suggested_avoid_physical_qubits', []))}`",
                f"- p01 threshold: {readout_diagnostics.get('p01_threshold')}",
                f"- p10 threshold: {readout_diagnostics.get('p10_threshold')}",
                f"- step-0 flip threshold: {readout_diagnostics.get('step0_flip_threshold')}",
                "",
            ]
        )
        flagged = readout_diagnostics.get("flagged_rows", [])
        if flagged:
            lines.extend(
                [
                    "| cbit | physical | site | spin | p01 | p10 | step0 flip | flags |",
                    "|---:|---:|---:|---|---:|---:|---:|---|",
                ]
            )
            for row in flagged:
                lines.append(
                    f"| {row['cbit']} | {row['physical_qubit']} | {row['site']} | {row['spin']} | "
                    f"{row['p01_meas1_given_0']:.6f} | {row['p10_meas0_given_1']:.6f} | "
                    f"{row['step0_flip_rate']} | {row['flags']} |"
                )
        else:
            lines.append("No readout/step-0 outliers were flagged.")
        lines.append("")

    lines.extend(
        [
        "## Echo depths",
        "",
        ]
    )
    if echo_data:
        lines.extend(
            [
                "| echo steps | ZNE factor | exact return | return / step-0 | sector survival | mean Hamming/qubit | CZ | twoq depth |",
                "|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for row in echo_data:
            lines.append(
                f"| {row['echo_steps']} | {row.get('zne_noise_factor', 1)} | {row['return_probability']:.6f} +- {row['return_probability_stderr']:.6f} | "
                f"{row['return_probability_normalized_by_step0']} | {row['sector_survival']:.6f} | "
                f"{row['mean_hamming_distance']:.6f} | {row['transpiled_cz_count']} | {row['transpiled_two_qubit_depth']} |"
            )
    else:
        lines.append("No echo circuits were available in this stage.")

    if echo_zne_data:
        lines.extend(
            [
                "",
                "## Echo ZNE",
                "",
                "| echo steps | factors | ZNE exact return | ZNE return / step-0 | ZNE sector survival | ZNE mean Hamming/qubit |",
                "|---:|---|---:|---:|---:|---:|",
            ]
        )
        for row in echo_zne_data:
            lines.append(
                f"| {row['echo_steps']} | {row['zne_noise_factors']} | "
                f"{row['return_probability_zne_linear']:.6f} | "
                f"{row['return_probability_zne_linear_normalized_by_step0']} | "
                f"{row['sector_survival_zne_linear']:.6f} | "
                f"{row['mean_hamming_zne_linear']:.6f} |"
            )

    lines.extend(
        [
            "",
            "## Warnings",
            "",
        ]
    )
    lines.extend(f"- {warning}" for warning in warnings)
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "If the step-0 echo is already low, initialization/readout/layout dominate. "
            "If step-0 is high but the curve decays quickly with echo steps, the loss is "
            "mostly circuit-depth and CZ scheduling. That is the point where a native "
            "fSWAP/CZ circuit rewrite is the right next lever.",
            "",
        ]
    )
    md_path.write_text("\n".join(lines))
    return summary_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True, help="Stage directory, for example .../q20_steps4")
    parser.add_argument("--raw-results", type=Path, default=None, help="Reuse an existing raw-results JSON instead of fetching jobs")
    parser.add_argument("--refresh", action="store_true", help="Fetch Runtime jobs even when ibm_staged_raw_results.json exists")
    parser.add_argument("--max-noiseless-qubits", type=int, default=24)
    parser.add_argument(
        "--reference-observables",
        type=Path,
        default=None,
        help=(
            "External observable reference as JSON or CSV. Use this for large stages "
            "where exact statevector references are unavailable."
        ),
    )
    parser.add_argument(
        "--frontier-soft-sector",
        action="store_true",
        help=(
            "Opt-in diagnostic route: soft particle-sector reweighting of the main counts. "
            "This does not run by default and is not selected as the headline profile."
        ),
    )
    parser.add_argument(
        "--frontier-sector-lambda",
        type=float,
        default=0.05,
        help="Soft-sector penalty strength used with --frontier-soft-sector.",
    )
    parser.add_argument(
        "--frontier-linear-sector-penalty",
        action="store_true",
        help="Use |dN_up|+|dN_down| instead of squared sector penalty for the opt-in soft-sector route.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    stage_dir = args.run_dir
    plan_path = stage_dir / "stage_plan.json"
    if not plan_path.exists():
        raise FileNotFoundError(f"Missing {plan_path}")

    plan = json.loads(plan_path.read_text())
    cfg = config_from_stage_plan(plan)
    mapping = semantic_mapping_from_plan(plan, cfg)
    cbit_to_mode = mode_by_classical_bit(mapping)
    if len(cbit_to_mode) != cfg.qubits:
        raise ValueError("semantic mapping does not define one classical bit per qubit")
    raw_results = load_raw_results(stage_dir, cfg.qubits, args.raw_results, args.refresh)
    submitted_jobs = load_submitted_jobs(stage_dir)

    counts_by_factor = main_counts_by_zne_factor(raw_results, submitted_jobs, cfg)
    if not counts_by_factor:
        raise ValueError("No main result pubs found")
    counts = counts_by_factor.get(1, next(iter(counts_by_factor.values())))
    p01, p10, readout_meta = readout_params(raw_results, cfg)
    final_echo_counts = echo_counts_for_step(
        raw_results,
        submitted_jobs,
        cfg,
        echo_step=cfg.steps,
        zne_noise_factor=1,
    )
    local_rows, nominal_profiles = charge_profiles_from_counts(
        counts=counts,
        echo_counts_data=final_echo_counts,
        cfg=cfg,
        mapping=mapping,
        cbit_to_mode=cbit_to_mode,
        p01=p01,
        p10=p10,
    )
    raw_charge = nominal_profiles["raw"]
    if raw_charge is None:
        raise ValueError("Local observable rows did not produce one up/down pair per site")
    ideal_observable_profile = None
    if args.reference_observables is not None:
        ideal_observable_profile = load_external_observable_reference(args.reference_observables, cfg)
    else:
        ideal_observable_profile = noiseless_observable_profile(cfg, cbit_to_mode, args.max_noiseless_qubits)
    ideal_charge = profile_site_values(ideal_observable_profile, "charge")
    if ideal_charge is None and args.reference_observables is None:
        ideal_charge = noiseless_charge_density(cfg, args.max_noiseless_qubits)

    charge_profiles: dict[str, list[float] | None] = {
        "raw": nominal_profiles["raw"],
        "readout_corrected": nominal_profiles["readout_corrected"],
        "readout_and_decay_recovered": nominal_profiles["readout_and_decay_recovered"],
        "symmetry_raw": None,
        "symmetry_readout_corrected": None,
        "zne_readout_corrected": None,
        "zne_symmetry_readout_corrected": None,
    }

    sym_counts, sym_meta = postselect_counts_by_mapping(counts, cfg, cbit_to_mode)
    symmetry_postselection: dict[str, Any] = {
        "requested_in_config": cfg.mitigation.symmetry_postselection,
        "applied_in_summary": True,
        "nominal": sym_meta,
        "by_zne_factor": {},
        "headline_candidate": cfg.mitigation.symmetry_postselection,
    }
    if sym_counts:
        _sym_rows, sym_profiles = charge_profiles_from_counts(
            counts=sym_counts,
            echo_counts_data=None,
            cfg=cfg,
            mapping=mapping,
            cbit_to_mode=cbit_to_mode,
            p01=p01,
            p10=p10,
        )
        charge_profiles["symmetry_raw"] = sym_profiles["raw"]
        charge_profiles["symmetry_readout_corrected"] = sym_profiles["readout_corrected"]

    frontier_soft_counts = None
    if args.frontier_soft_sector:
        frontier_soft_counts, frontier_soft_meta = soft_sector_reweight_counts(
            counts,
            cfg=cfg,
            cbit_to_mode=cbit_to_mode,
            lambda_sector=args.frontier_sector_lambda,
            linear_penalty=args.frontier_linear_sector_penalty,
        )
        symmetry_postselection["frontier_soft_sector"] = frontier_soft_meta
        _frontier_soft_rows, frontier_soft_profiles = charge_profiles_from_counts(
            counts=frontier_soft_counts,
            echo_counts_data=None,
            cfg=cfg,
            mapping=mapping,
            cbit_to_mode=cbit_to_mode,
            p01=p01,
            p10=p10,
        )
        charge_profiles["frontier_soft_sector_raw"] = frontier_soft_profiles["raw"]
        charge_profiles["frontier_soft_sector_readout_corrected"] = frontier_soft_profiles["readout_corrected"]

    zne_readout_by_factor: dict[int, list[float] | None] = {}
    zne_symmetry_readout_by_factor: dict[int, list[float] | None] = {}
    for factor, factor_counts in counts_by_factor.items():
        _factor_rows, factor_profiles = charge_profiles_from_counts(
            counts=factor_counts,
            echo_counts_data=None,
            cfg=cfg,
            mapping=mapping,
            cbit_to_mode=cbit_to_mode,
            p01=p01,
            p10=p10,
        )
        zne_readout_by_factor[factor] = factor_profiles["readout_corrected"] or factor_profiles["raw"]
        factor_sym_counts, factor_sym_meta = postselect_counts_by_mapping(factor_counts, cfg, cbit_to_mode)
        symmetry_postselection["by_zne_factor"][str(factor)] = factor_sym_meta
        if factor_sym_counts:
            _factor_sym_rows, factor_sym_profiles = charge_profiles_from_counts(
                counts=factor_sym_counts,
                echo_counts_data=None,
                cfg=cfg,
                mapping=mapping,
                cbit_to_mode=cbit_to_mode,
                p01=p01,
                p10=p10,
            )
            zne_symmetry_readout_by_factor[factor] = (
                factor_sym_profiles["readout_corrected"] or factor_sym_profiles["raw"]
            )
        else:
            zne_symmetry_readout_by_factor[factor] = None

    charge_profiles["zne_readout_corrected"] = linear_zne_profile(zne_readout_by_factor, cfg.sites)
    charge_profiles["zne_symmetry_readout_corrected"] = linear_zne_profile(zne_symmetry_readout_by_factor, cfg.sites)

    zne_charge_metadata = {
        "enabled_in_config": cfg.mitigation.zne_mitigation,
        "noise_factors": sorted(counts_by_factor),
        "extrapolator": cfg.mitigation.zne_extrapolator,
        "fold_scope": cfg.mitigation.zne_fold_scope,
        "readout_factor_count": len([value for value in zne_readout_by_factor.values() if value is not None]),
        "symmetry_factor_count": len([value for value in zne_symmetry_readout_by_factor.values() if value is not None]),
        "available_profiles": [
            name
            for name in ("zne_readout_corrected", "zne_symmetry_readout_corrected")
            if charge_profiles.get(name) is not None
        ],
    }

    observable_profiles: dict[str, dict[str, Any] | None] = {
        "raw": observable_profile_from_counts(counts, cfg, cbit_to_mode),
        "readout_corrected": None
        if p01 is None or p10 is None
        else observable_profile_from_counts(counts, cfg, cbit_to_mode, p01, p10, readout_corrected=True),
        "symmetry_raw": None,
        "symmetry_readout_corrected": None,
        "zne_readout_corrected": None,
        "zne_symmetry_readout_corrected": None,
    }
    if sym_counts:
        observable_profiles["symmetry_raw"] = observable_profile_from_counts(sym_counts, cfg, cbit_to_mode)
        observable_profiles["symmetry_readout_corrected"] = (
            None
            if p01 is None or p10 is None
            else observable_profile_from_counts(sym_counts, cfg, cbit_to_mode, p01, p10, readout_corrected=True)
        )
    if frontier_soft_counts is not None:
        observable_profiles["frontier_soft_sector_raw"] = observable_profile_from_counts(
            frontier_soft_counts,
            cfg,
            cbit_to_mode,
        )
        observable_profiles["frontier_soft_sector_readout_corrected"] = (
            None
            if p01 is None or p10 is None
            else observable_profile_from_counts(
                frontier_soft_counts,
                cfg,
                cbit_to_mode,
                p01,
                p10,
                readout_corrected=True,
            )
        )

    zne_observable_by_factor: dict[int, dict[str, Any] | None] = {}
    zne_symmetry_observable_by_factor: dict[int, dict[str, Any] | None] = {}
    for factor, factor_counts in counts_by_factor.items():
        zne_observable_by_factor[factor] = observable_profile_from_counts(
            factor_counts,
            cfg,
            cbit_to_mode,
            p01,
            p10,
            readout_corrected=p01 is not None and p10 is not None,
        )
        factor_sym_counts, _factor_sym_meta = postselect_counts_by_mapping(factor_counts, cfg, cbit_to_mode)
        zne_symmetry_observable_by_factor[factor] = (
            None
            if not factor_sym_counts
            else observable_profile_from_counts(
                factor_sym_counts,
                cfg,
                cbit_to_mode,
                p01,
                p10,
                readout_corrected=p01 is not None and p10 is not None,
            )
        )
    observable_profiles["zne_readout_corrected"] = linear_zne_observable_profile(
        zne_observable_by_factor,
        cfg,
    )
    observable_profiles["zne_symmetry_readout_corrected"] = linear_zne_observable_profile(
        zne_symmetry_observable_by_factor,
        cfg,
    )
    observable_route_rows_data = observable_route_rows(observable_profiles, ideal_observable_profile, cfg)

    headline_candidates = dict(charge_profiles)
    sym_discard_rate = sym_meta.get("discard_rate")
    allow_symmetry_headline = (
        cfg.mitigation.symmetry_postselection
        and sym_discard_rate is not None
        and float(sym_discard_rate) <= 0.5
    )
    symmetry_postselection["headline_candidate"] = allow_symmetry_headline
    if not allow_symmetry_headline:
        for name in ("symmetry_raw", "symmetry_readout_corrected", "zne_symmetry_readout_corrected"):
            headline_candidates[name] = None
    for name in list(headline_candidates):
        if name.startswith("frontier_soft_sector"):
            headline_candidates[name] = None
    headline_profile, _headline_charge, charge_profile_rmses = choose_headline_profile(
        headline_candidates,
        ideal_charge,
    )
    charge_profile_rmses = {
        name: rmse(charge, ideal_charge)
        for name, charge in charge_profiles.items()
    } | {
        "headline": rmse(charge_profiles.get(headline_profile), ideal_charge),
    }

    local_observables_csv = write_local_observable_artifact(stage_dir, local_rows)
    observable_suite_csv, observable_route_csv, observable_suite_plot = write_observable_suite_artifacts(
        stage_dir,
        cfg,
        observable_profiles,
        observable_route_rows_data,
        ideal_observable_profile,
    )
    charge_csv, charge_plot = write_charge_artifacts(
        stage_dir,
        cfg,
        charge_profiles,
        headline_profile,
        ideal_charge,
    )
    explicit_steps = plan.get("echo_steps")
    echo_data = echo_rows(
        raw_results,
        cfg,
        str(plan.get("echo_policy", "final")),
        explicit_steps,
        mapping,
        submitted_jobs,
        p01,
        p10,
    )
    echo_zne_data = zne_echo_rows(echo_data)
    readout_rows, readout_diagnostics = readout_diagnostic_rows(
        cfg=cfg,
        mapping=mapping,
        layout=plan.get("layout_selection", {}),
        p01=p01,
        p10=p10,
        echo_data=echo_data,
    )
    bad_qubits_csv = write_readout_diagnostic_artifact(stage_dir, readout_rows)
    echo_csv, echo_plot = write_echo_artifacts(stage_dir, echo_data)
    echo_zne_csv, echo_zne_plot = write_zne_echo_artifacts(stage_dir, echo_zne_data)

    artifacts = {
        "raw_results": repo_relative_path(stage_dir / "ibm_staged_raw_results.json"),
        "charge_csv": repo_relative_path(charge_csv),
        "charge_plot": repo_relative_path(charge_plot),
        "echo_csv": repo_relative_path(echo_csv),
        "echo_plot": repo_relative_path(echo_plot),
        "echo_zne_csv": repo_relative_path(echo_zne_csv),
        "echo_zne_plot": repo_relative_path(echo_zne_plot),
        "local_observables_csv": repo_relative_path(local_observables_csv),
        "observable_suite_csv": repo_relative_path(observable_suite_csv),
        "observable_route_scores_csv": repo_relative_path(observable_route_csv),
        "observable_suite_plot": repo_relative_path(observable_suite_plot),
        "bad_qubits_csv": repo_relative_path(bad_qubits_csv),
    }
    summary_json, summary_md = write_summary(
        stage_dir,
        cfg,
        plan,
        mapping,
        raw_results,
        readout_meta,
        charge_profiles,
        charge_profile_rmses,
        headline_profile,
        symmetry_postselection,
        zne_charge_metadata,
        local_rows,
        observable_profiles,
        observable_route_rows_data,
        ideal_observable_profile,
        readout_diagnostics,
        echo_data,
        echo_zne_data,
        artifacts,
        args.max_noiseless_qubits,
    )
    print(f"Wrote {summary_json}")
    print(f"Wrote {summary_md}")


if __name__ == "__main__":
    main()
