#!/usr/bin/env python3
"""Separate 2D cuprate-oriented Hubbard pipeline.

This pipeline is deliberately separate from the existing 1D 60q/120q pipeline.
It prepares an auditable target problem for cuprate-like 2D Hubbard physics:

  - square-lattice one-band Hubbard model with optional t'
  - hole-doped Neel initial state for short-time dynamics
  - explicit row-major Jordan-Wigner mode map
  - diagonal and non-diagonal observable plan, including d-wave pairing
  - rough explicit-JW resource estimates
  - comparison target registry from classical papers, datasets, and measurements

It does not claim superconductivity. The d-wave observables are a measurement
plan; actual evidence needs reference data and off-diagonal correlator
estimation, not only Z-basis charge/spin readout.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np


SPIN_UP = "up"
SPIN_DOWN = "down"
SPINS = (SPIN_UP, SPIN_DOWN)


@dataclass(frozen=True)
class Cuprate2DConfig:
    lx: int = 6
    ly: int = 6
    holes: int = 4
    hopping_t: float = 1.0
    t_prime_over_t: float = -0.25
    u_over_t: float = 8.0
    chemical_potential: float = 0.0
    steps: int = 4
    dt: float = 0.1
    boundary_x: str = "open"
    boundary_y: str = "open"
    initial_state: str = "stripe_neel"
    shots: int = 20_000

    @property
    def sites(self) -> int:
        return self.lx * self.ly

    @property
    def qubits(self) -> int:
        return 2 * self.sites

    @property
    def electrons(self) -> int:
        return self.sites - self.holes

    @property
    def hole_doping(self) -> float:
        return self.holes / self.sites

    @property
    def interaction_u(self) -> float:
        return self.u_over_t * self.hopping_t

    @property
    def t_prime(self) -> float:
        return self.t_prime_over_t * self.hopping_t

    @property
    def total_time(self) -> float:
        return self.steps * self.dt


@dataclass(frozen=True)
class ReferenceTarget:
    target_id: str
    kind: str
    title: str
    url: str
    doi: str
    parameters: str
    useful_for: str
    compare_to: str
    caveat: str
    priority: str


def validate_config(cfg: Cuprate2DConfig) -> None:
    if cfg.lx <= 1 or cfg.ly <= 1:
        raise ValueError("lx and ly must both be greater than 1")
    if cfg.holes < 0 or cfg.holes >= cfg.sites:
        raise ValueError("holes must satisfy 0 <= holes < lx*ly")
    if cfg.boundary_x not in {"open", "periodic"}:
        raise ValueError("boundary_x must be 'open' or 'periodic'")
    if cfg.boundary_y not in {"open", "periodic"}:
        raise ValueError("boundary_y must be 'open' or 'periodic'")
    if cfg.steps < 0:
        raise ValueError("steps must be non-negative")
    if cfg.dt <= 0:
        raise ValueError("dt must be positive")


def site_index(cfg: Cuprate2DConfig, x: int, y: int) -> int:
    return y * cfg.lx + x


def site_coord(cfg: Cuprate2DConfig, site: int) -> tuple[int, int]:
    return site % cfg.lx, site // cfg.lx


def mode_qubit(site: int, spin: str) -> int:
    if spin == SPIN_UP:
        return 2 * site
    if spin == SPIN_DOWN:
        return 2 * site + 1
    raise ValueError(f"unknown spin: {spin}")


def neighbor_site(cfg: Cuprate2DConfig, x: int, y: int, dx: int, dy: int) -> int | None:
    nx = x + dx
    ny = y + dy
    if nx < 0 or nx >= cfg.lx:
        if cfg.boundary_x == "periodic":
            nx %= cfg.lx
        else:
            return None
    if ny < 0 or ny >= cfg.ly:
        if cfg.boundary_y == "periodic":
            ny %= cfg.ly
        else:
            return None
    return site_index(cfg, nx, ny)


def unique_bonds(
    cfg: Cuprate2DConfig,
    directions: Iterable[tuple[int, int, str]],
    coefficient: float,
    family: str,
) -> list[dict[str, Any]]:
    seen: set[tuple[int, int, str]] = set()
    bonds: list[dict[str, Any]] = []
    for y in range(cfg.ly):
        for x in range(cfg.lx):
            left = site_index(cfg, x, y)
            for dx, dy, orientation in directions:
                right = neighbor_site(cfg, x, y, dx, dy)
                if right is None or right == left:
                    continue
                a, b = sorted((left, right))
                key = (a, b, family)
                if key in seen:
                    continue
                seen.add(key)
                ax, ay = site_coord(cfg, a)
                bx, by = site_coord(cfg, b)
                bonds.append(
                    {
                        "family": family,
                        "orientation": orientation,
                        "site_a": a,
                        "x_a": ax,
                        "y_a": ay,
                        "site_b": b,
                        "x_b": bx,
                        "y_b": by,
                        "coefficient": coefficient,
                    }
                )
    return bonds


def nearest_neighbor_bonds(cfg: Cuprate2DConfig) -> list[dict[str, Any]]:
    return unique_bonds(
        cfg,
        directions=[(1, 0, "x"), (0, 1, "y")],
        coefficient=-cfg.hopping_t,
        family="nearest_t",
    )


def next_nearest_neighbor_bonds(cfg: Cuprate2DConfig) -> list[dict[str, Any]]:
    if abs(cfg.t_prime) < 1e-15:
        return []
    return unique_bonds(
        cfg,
        directions=[(1, 1, "diag_pos"), (1, -1, "diag_neg")],
        coefficient=-cfg.t_prime,
        family="next_nearest_t_prime",
    )


def all_hopping_bonds(cfg: Cuprate2DConfig) -> list[dict[str, Any]]:
    return nearest_neighbor_bonds(cfg) + next_nearest_neighbor_bonds(cfg)


def ranked_hole_candidates(cfg: Cuprate2DConfig) -> list[int]:
    center_x = 0.5 * (cfg.lx - 1)
    center_y = 0.5 * (cfg.ly - 1)
    sites = list(range(cfg.sites))

    if cfg.initial_state == "center_neel":
        return sorted(
            sites,
            key=lambda site: (
                (site_coord(cfg, site)[0] - center_x) ** 2 + (site_coord(cfg, site)[1] - center_y) ** 2,
                site,
            ),
        )

    if cfg.initial_state != "stripe_neel":
        raise ValueError("initial_state must be 'stripe_neel' or 'center_neel'")

    return sorted(
        sites,
        key=lambda site: (
            abs(site_coord(cfg, site)[0] - center_x),
            abs(site_coord(cfg, site)[1] - center_y),
            site_coord(cfg, site)[1],
            site_coord(cfg, site)[0],
        ),
    )


def select_hole_sites(cfg: Cuprate2DConfig) -> set[int]:
    candidates = ranked_hole_candidates(cfg)
    selected: list[int] = []
    selected_set: set[int] = set()
    sublattice_order = [0, 1]
    while len(selected) < cfg.holes:
        wanted = sublattice_order[len(selected) % len(sublattice_order)]
        match = next(
            (
                site
                for site in candidates
                if site not in selected_set and sum(site_coord(cfg, site)) % 2 == wanted
            ),
            None,
        )
        if match is None:
            match = next(site for site in candidates if site not in selected_set)
        selected.append(match)
        selected_set.add(match)
    return selected_set


def initial_site_rows(cfg: Cuprate2DConfig) -> list[dict[str, Any]]:
    holes = select_hole_sites(cfg)
    rows: list[dict[str, Any]] = []
    for site in range(cfg.sites):
        x, y = site_coord(cfg, site)
        is_hole = site in holes
        up = 0
        down = 0
        if not is_hole:
            if (x + y) % 2 == 0:
                up = 1
            else:
                down = 1
        rows.append(
            {
                "site": site,
                "x": x,
                "y": y,
                "hole": int(is_hole),
                "n_up_initial": up,
                "n_down_initial": down,
                "charge_initial": up + down,
                "spin_z_initial": up - down,
                "up_qubit": mode_qubit(site, SPIN_UP),
                "down_qubit": mode_qubit(site, SPIN_DOWN),
            }
        )
    return rows


def mode_order(cfg: Cuprate2DConfig) -> list[dict[str, Any]]:
    modes = []
    for site in range(cfg.sites):
        x, y = site_coord(cfg, site)
        for spin in SPINS:
            modes.append(
                {
                    "logical_qubit": mode_qubit(site, spin),
                    "site": site,
                    "x": x,
                    "y": y,
                    "spin": spin,
                }
            )
    return modes


def jw_string_weight(p: int, q: int) -> int:
    return abs(int(p) - int(q)) + 1


def resource_estimate(cfg: Cuprate2DConfig, bonds: list[dict[str, Any]]) -> dict[str, Any]:
    hopping_terms = []
    total_hopping_pauli_rotations = 0
    total_hopping_rough_cnot = 0
    max_weight = 0
    for bond in bonds:
        for spin in SPINS:
            qa = mode_qubit(int(bond["site_a"]), spin)
            qb = mode_qubit(int(bond["site_b"]), spin)
            weight = jw_string_weight(qa, qb)
            max_weight = max(max_weight, weight)
            rotations = 2
            rough_cnot = rotations * 2 * (weight - 1)
            total_hopping_pauli_rotations += rotations
            total_hopping_rough_cnot += rough_cnot
            hopping_terms.append(
                {
                    "family": bond["family"],
                    "orientation": bond["orientation"],
                    "spin": spin,
                    "site_a": bond["site_a"],
                    "site_b": bond["site_b"],
                    "qubit_a": qa,
                    "qubit_b": qb,
                    "jw_string_weight": weight,
                    "pauli_rotations": rotations,
                    "rough_cnot_ladder_count": rough_cnot,
                }
            )

    onsite_zz_rotations = cfg.sites
    onsite_rough_cnot = 2 * cfg.sites
    per_step_rough_cnot = total_hopping_rough_cnot + onsite_rough_cnot
    return {
        "estimate_kind": "explicit_row_major_jordan_wigner_first_order_trotter",
        "claim_boundary": (
            "Rough explicit-JW gate accounting only. This is not a hardware-optimized "
            "2D fermionic routing or fSWAP compilation."
        ),
        "sites": cfg.sites,
        "qubits": cfg.qubits,
        "nearest_neighbor_bonds": len([b for b in bonds if b["family"] == "nearest_t"]),
        "next_nearest_neighbor_bonds": len([b for b in bonds if b["family"] == "next_nearest_t_prime"]),
        "onsite_zz_rotations_per_step": onsite_zz_rotations,
        "hopping_pauli_rotations_per_step": total_hopping_pauli_rotations,
        "max_jw_string_weight": max_weight,
        "rough_cnot_ladder_count_per_step": per_step_rough_cnot,
        "rough_cnot_ladder_count_total": per_step_rough_cnot * cfg.steps,
        "hopping_terms": hopping_terms,
    }


def pairing_components_for_site(cfg: Cuprate2DConfig, site: int) -> list[dict[str, Any]]:
    x, y = site_coord(cfg, site)
    components = []
    for dx, dy, label, sign in [
        (1, 0, "plus_x", 1.0),
        (-1, 0, "minus_x", 1.0),
        (0, 1, "plus_y", -1.0),
        (0, -1, "minus_y", -1.0),
    ]:
        other = neighbor_site(cfg, x, y, dx, dy)
        if other is None or other == site:
            continue
        components.append(
            {
                "component": label,
                "sign": sign,
                "site_i": site,
                "site_j": other,
                "definition": "singlet_pair_c_i_up_c_j_down_minus_c_i_down_c_j_up",
            }
        )
    return components


def observable_plan(cfg: Cuprate2DConfig, bonds: list[dict[str, Any]]) -> dict[str, Any]:
    density_rows = []
    for site in range(cfg.sites):
        x, y = site_coord(cfg, site)
        density_rows.append(
            {
                "site": site,
                "x": x,
                "y": y,
                "n_up_qubit": mode_qubit(site, SPIN_UP),
                "n_down_qubit": mode_qubit(site, SPIN_DOWN),
                "charge": "n_up + n_down",
                "spin_z": "n_up - n_down",
                "double_occupancy": "n_up * n_down",
                "hole_density": "1 - charge",
            }
        )

    nearest = [bond for bond in bonds if bond["family"] == "nearest_t"]
    pair_centers = [
        {
            "site": site,
            "x": site_coord(cfg, site)[0],
            "y": site_coord(cfg, site)[1],
            "d_wave_components": pairing_components_for_site(cfg, site),
        }
        for site in range(cfg.sites)
    ]
    pair_centers = [item for item in pair_centers if len(item["d_wave_components"]) >= 2]

    return {
        "diagonal_z_basis": {
            "site_observables": density_rows,
            "bond_observables": [
                {
                    "bond": f"{bond['site_a']}-{bond['site_b']}",
                    "orientation": bond["orientation"],
                    "charge_correlation": "<n_i n_j>",
                    "spin_correlation": "<(n_i_up-n_i_down)(n_j_up-n_j_down)>",
                }
                for bond in nearest
            ],
            "structure_factors": [
                {
                    "name": "antiferromagnetic_spin_structure",
                    "wavevector": "(pi, pi)",
                    "formula": "S_s(q)=sum_ij exp(i q.(r_i-r_j)) <S_i^z S_j^z> / N",
                },
                {
                    "name": "vertical_charge_stripe_structure",
                    "wavevector": "(pi/2, 0) for period-4 charge modulation",
                    "formula": "S_c(q)=sum_ij exp(i q.(r_i-r_j)) <delta_n_i delta_n_j> / N",
                },
            ],
        },
        "off_diagonal_pairing": {
            "d_wave_pair_center_definition": (
                "Delta_d(i)=0.5*(Delta_i,+x + Delta_i,-x - Delta_i,+y - Delta_i,-y), "
                "with singlet bond Delta_ij=c_i_up c_j_down - c_i_down c_j_up"
            ),
            "pair_centers": pair_centers,
            "pair_correlator": "<Delta_d^dagger(i) Delta_d(j)>",
            "measurement_note": (
                "These are four-fermion off-diagonal correlators. They require additional "
                "basis rotations or dedicated fermionic tomography circuits; they cannot be "
                "recovered from the existing charge/spin Z-basis pipeline alone."
            ),
        },
    }


def reference_targets() -> list[ReferenceTarget]:
    return [
        ReferenceTarget(
            target_id="leblanc_2015_prx_benchmarks",
            kind="classical_arxiv",
            title="Solutions of the Two Dimensional Hubbard Model: Benchmarks and Results from a Wide Range of Numerical Algorithms",
            url="https://arxiv.org/abs/1505.02290",
            doi="10.1103/PhysRevX.5.041041",
            parameters="2D square-lattice one-band Hubbard; energies, double occupancy, self energies.",
            useful_for="Baseline sanity checks before any superconductivity framing.",
            compare_to="energy, double occupancy, density, small-cluster exact/reference runs",
            caveat="Not a cuprate measurement; mainly a numerical benchmark suite.",
            priority="high",
        ),
        ReferenceTarget(
            target_id="qin_2016_afqmc_benchmark",
            kind="classical_arxiv",
            title="Benchmark study of the two-dimensional Hubbard model with auxiliary-field quantum Monte Carlo method",
            url="https://arxiv.org/abs/1605.09421",
            doi="10.1103/PhysRevB.94.085103",
            parameters="U/t=2..8; densities including n=0.875; finite sizes up to 16x16.",
            useful_for="Direct AFQMC comparison near 1/8 hole doping.",
            compare_to="energy, double occupancy, spin/magnetization, momentum distribution",
            caveat="Away from half filling uses constrained-path control of the sign problem.",
            priority="high",
        ),
        ReferenceTarget(
            target_id="zheng_2017_science_stripes",
            kind="classical_arxiv",
            title="Stripe order in the underdoped region of the two-dimensional Hubbard model",
            url="https://arxiv.org/abs/1701.00054",
            doi="10.1126/science.aam7127",
            parameters="Underdoped 2D Hubbard, multi-method ground-state stripe comparison.",
            useful_for="Charge/spin stripe observables and wavelength checks.",
            compare_to="charge stripe structure factor, spin stripe structure factor, stripe filling",
            caveat="Found filled stripe order in the pure model that differs from real cuprates.",
            priority="high",
        ),
        ReferenceTarget(
            target_id="qin_2020_prx_absence_pure_model",
            kind="classical_arxiv",
            title="Absence of superconductivity in the pure two-dimensional Hubbard model",
            url="https://arxiv.org/abs/1910.08931",
            doi="10.1103/PhysRevX.10.031016",
            parameters="Pure nearest-neighbor 2D Hubbard, intermediate to strong coupling, near optimal doping.",
            useful_for="Negative control: t'=0 should not be sold as established d-wave superconductivity.",
            compare_to="long-distance d-wave pair correlations",
            caveat="Pure t'=0 model; not the same as cuprate-like t'<0 target.",
            priority="high",
        ),
        ReferenceTarget(
            target_id="xu_2024_science_tp_stripes_superconductivity",
            kind="classical_arxiv",
            title="Coexistence of superconductivity with partially filled stripes in the Hubbard model",
            url="https://arxiv.org/abs/2303.08376",
            doi="10.1126/science.adh7691",
            parameters="2D Hubbard with next-nearest-neighbor hopping t'; DMRG plus AFQMC.",
            useful_for="Main cuprate-like comparison target for t'<0 and d-wave pairing.",
            compare_to="d-wave pair order/correlations, stripe filling, charge modulation, AF correlations",
            caveat="Tiny energy scales; needs careful size/boundary extrapolation.",
            priority="highest",
        ),
        ReferenceTarget(
            target_id="mai_2022_pnas_dca_dataset",
            kind="classical_dataset",
            title="Intertwined spin, charge and pair correlations in the two-dimensional Hubbard model in the thermodynamic limit",
            url="https://arxiv.org/abs/2106.01944",
            doi="10.1073/pnas.2112806119; data: 10.5281/zenodo.5904352",
            parameters="DCA/DQMC thermodynamic-limit study with raw and processed data on Zenodo.",
            useful_for="Direct downloadable data target for spin, charge, pair, and pair-density-wave correlations.",
            compare_to="spin/charge/pair correlation functions and structure factors",
            caveat="Embedded-cluster method; match parameters before numeric comparison.",
            priority="highest",
        ),
        ReferenceTarget(
            target_id="wietek_2021_prx_finite_temperature",
            kind="classical_arxiv",
            title="Stripes, Antiferromagnetism, and the Pseudogap in the Doped Hubbard Model at Finite Temperature",
            url="https://arxiv.org/abs/2009.10736",
            doi="10.1103/PhysRevX.11.031007",
            parameters="Strong-coupling doped 2D Hubbard on width-4 cylinders using METTS.",
            useful_for="Finite-temperature stripe/pseudogap comparison and AF-to-stripe crossover.",
            compare_to="spin correlations, charge order, specific heat/susceptibility proxies",
            caveat="Finite temperature and cylinder geometry; not a direct hardware-time trace.",
            priority="medium",
        ),
        ReferenceTarget(
            target_id="chiu_2019_science_string_patterns",
            kind="quantum_gas_measurement",
            title="String patterns in the doped Hubbard model",
            url="https://arxiv.org/abs/1810.03584",
            doi="10.1126/science.aav3587; data: 10.7910/DVN/1CSVBV",
            parameters="Cold-atom doped Hubbard antiferromagnet snapshots.",
            useful_for="Experimental comparison for hole motion through an AF background.",
            compare_to="hole-spin patterns, geometric-string observables, spin-charge diagnostics",
            caveat="Analog cold-atom simulator, not electronic cuprate material and not d-wave SC.",
            priority="medium",
        ),
        ReferenceTarget(
            target_id="kendrick_2025_arxiv_pseudogap_quantum_simulator",
            kind="quantum_gas_measurement",
            title="Pseudogap in a Fermi-Hubbard quantum simulator",
            url="https://arxiv.org/abs/2509.18075",
            doi="10.48550/arXiv.2509.18075",
            parameters="Cold-atom thermodynamic and spectroscopic measurements versus doping and U/t.",
            useful_for="Experimental pseudogap/metal crossover target.",
            compare_to="compressibility proxy, spectral response proxy, doping phase boundary",
            caveat="Recent arXiv preprint; not a local-pairing or d-wave order measurement.",
            priority="medium",
        ),
        ReferenceTarget(
            target_id="hashimoto_2015_arpes_cuprate_gaps",
            kind="cuprate_measurement_review",
            title="Energy gaps in high-transition temperature cuprate superconductors",
            url="https://arxiv.org/abs/1503.00391",
            doi="arXiv:1503.00391",
            parameters="ARPES phenomenology of superconducting gap and pseudogap in cuprates.",
            useful_for="Qualitative real-material d-wave gap and pseudogap comparison.",
            compare_to="momentum-space d-wave symmetry and pseudogap phenomenology, not local Z observables",
            caveat="Real cuprates include material chemistry beyond the one-band Hubbard model.",
            priority="low",
        ),
        ReferenceTarget(
            target_id="comin_2015_rxs_charge_order_cuprates",
            kind="cuprate_measurement_review",
            title="Resonant x-ray scattering studies of charge order in cuprates",
            url="https://arxiv.org/abs/1509.03313",
            doi="10.1146/annurev-conmatphys-031115-011401",
            parameters="Review of resonant x-ray scattering charge order in copper oxides.",
            useful_for="Qualitative charge-order/stripe comparison against Hubbard charge structure factors.",
            compare_to="charge ordering wave vectors and doping trends",
            caveat="Phenomenological comparison only; not a direct one-band-Hubbard benchmark.",
            priority="low",
        ),
    ]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_initial_state_plot(path: Path, cfg: Cuprate2DConfig, rows: list[dict[str, Any]]) -> Path:
    charge = np.zeros((cfg.ly, cfg.lx), dtype=float)
    spin = np.zeros((cfg.ly, cfg.lx), dtype=float)
    holes = np.zeros((cfg.ly, cfg.lx), dtype=float)
    for row in rows:
        x = int(row["x"])
        y = int(row["y"])
        charge[y, x] = float(row["charge_initial"])
        spin[y, x] = float(row["spin_z_initial"])
        holes[y, x] = float(row["hole"])

    try:
        import matplotlib.pyplot as plt
    except ModuleNotFoundError:
        text_path = path.with_suffix(".txt")
        if path.exists():
            path.unlink()
        lines = [
            f"2D Hubbard cuprate target: {cfg.lx}x{cfg.ly}, holes={cfg.holes}, U/t={cfg.u_over_t:g}, t'/t={cfg.t_prime_over_t:g}",
            "",
            "charge_initial:",
            *[" ".join(f"{int(value):1d}" for value in charge[y]) for y in reversed(range(cfg.ly))],
            "",
            "spin_z_initial:",
            *[" ".join(f"{int(value):2d}" for value in spin[y]) for y in reversed(range(cfg.ly))],
            "",
            "hole_mask:",
            *[" ".join(f"{int(value):1d}" for value in holes[y]) for y in reversed(range(cfg.ly))],
            "",
            "matplotlib was not available, so no PNG preview was generated.",
        ]
        text_path.write_text("\n".join(lines) + "\n")
        return text_path

    text_path = path.with_suffix(".txt")
    if text_path.exists():
        text_path.unlink()
    fig, axes = plt.subplots(1, 3, figsize=(11.0, 3.6), dpi=170, constrained_layout=True)
    panels = [
        (axes[0], charge, "initial charge", "viridis", 0.0, 1.0),
        (axes[1], spin, "initial spin z", "coolwarm", -1.0, 1.0),
        (axes[2], holes, "hole mask", "magma", 0.0, 1.0),
    ]
    for ax, data, title, cmap, vmin, vmax in panels:
        image = ax.imshow(data, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax)
        ax.set_title(title)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_xticks(range(cfg.lx))
        ax.set_yticks(range(cfg.ly))
        fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    fig.suptitle(f"2D Hubbard cuprate target: {cfg.lx}x{cfg.ly}, holes={cfg.holes}, U/t={cfg.u_over_t:g}, t'/t={cfg.t_prime_over_t:g}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return path


def write_reference_targets(outdir: Path) -> tuple[Path, Path]:
    targets = reference_targets()
    json_path = outdir / "cuprate_2d_reference_targets.json"
    md_path = outdir / "cuprate_2d_reference_targets.md"
    json_path.write_text(json.dumps([asdict(target) for target in targets], indent=2) + "\n")

    lines = [
        "# 2D Cuprate Hubbard Comparison Targets",
        "",
        "This file separates direct Hubbard benchmarks from real-material cuprate phenomenology.",
        "Use the high-priority classical targets first; real cuprate measurements are qualitative unless a material-specific mapping is added.",
        "",
        "| priority | kind | target | compare to | caveat |",
        "|---|---|---|---|---|",
    ]
    for target in targets:
        lines.append(
            f"| {target.priority} | {target.kind} | [{target.title}]({target.url}) | "
            f"{target.compare_to} | {target.caveat} |"
        )
    lines += [
        "",
        "Recommended order:",
        "",
        "1. Validate bookkeeping against LeBlanc 2015 and Qin 2016 style 2D Hubbard benchmarks.",
        "2. Use Zheng 2017, Xu 2024, and Mai 2022 for stripe and pairing observables.",
        "3. Use cold-atom measurements for experimental Hubbard patterns and pseudogap observables.",
        "4. Use ARPES/RXS cuprate measurements only as qualitative material motivation.",
        "",
    ]
    md_path.write_text("\n".join(lines))
    return json_path, md_path


def write_observable_flat_csv(path: Path, plan: dict[str, Any]) -> None:
    rows: list[dict[str, Any]] = []
    for item in plan["diagonal_z_basis"]["site_observables"]:
        rows.append(
            {
                "group": "site_z_basis",
                "name": f"site_{item['site']}",
                "observable": "charge/spin_z/double/hole_density",
                "requires": "Z-basis counts",
                "site_or_bond": item["site"],
            }
        )
    for item in plan["diagonal_z_basis"]["bond_observables"]:
        rows.append(
            {
                "group": "bond_z_basis",
                "name": item["bond"],
                "observable": "charge_correlation/spin_correlation",
                "requires": "Z-basis counts",
                "site_or_bond": item["bond"],
            }
        )
    for item in plan["off_diagonal_pairing"]["pair_centers"]:
        rows.append(
            {
                "group": "off_diagonal_pairing",
                "name": f"d_wave_center_{item['site']}",
                "observable": "d_wave_pair_correlator",
                "requires": "fermionic tomography or dedicated basis rotations",
                "site_or_bond": item["site"],
            }
        )
    write_csv(path, rows)


def write_report(
    outdir: Path,
    cfg: Cuprate2DConfig,
    bonds: list[dict[str, Any]],
    resources: dict[str, Any],
    artifacts: dict[str, Path],
) -> Path:
    md_path = outdir / "cuprate_2d_pipeline_report.md"
    nn = len([b for b in bonds if b["family"] == "nearest_t"])
    nnn = len([b for b in bonds if b["family"] == "next_nearest_t_prime"])
    lines = [
        "# 2D Cuprate Hubbard Pipeline",
        "",
        "Separate pipeline from the existing 1D 60q/120q Fermi-Hubbard workflow.",
        "",
        "## Target",
        "",
        f"- lattice: {cfg.lx}x{cfg.ly} square lattice",
        f"- sites/qubits: {cfg.sites}/{cfg.qubits}",
        f"- holes/doping: {cfg.holes}/{cfg.hole_doping:.6f}",
        f"- U/t: {cfg.u_over_t:g}",
        f"- t'/t: {cfg.t_prime_over_t:g}",
        f"- boundary: x={cfg.boundary_x}, y={cfg.boundary_y}",
        f"- Trotter sketch: steps={cfg.steps}, dt={cfg.dt:g}, total_time={cfg.total_time:g}",
        "",
        "## Generated Artifacts",
        "",
    ]
    for label, path in artifacts.items():
        lines.append(f"- {label}: `{path.as_posix()}`")
    lines += [
        "",
        "## Observable Boundary",
        "",
        "- Z-basis output can support charge density, spin-z density, doublons, and diagonal spin/charge correlations.",
        "- d-wave superconductivity needs off-diagonal pair correlators such as `<Delta_d^dagger(i) Delta_d(j)>`.",
        "- Stripe evidence should be reported through charge/spin structure factors and real-space modulation, not by visual inspection only.",
        "",
        "## Rough Explicit-JW Resources",
        "",
        f"- nearest-neighbor bonds: {nn}",
        f"- next-nearest-neighbor t' bonds: {nnn}",
        f"- hopping Pauli rotations per step: {resources['hopping_pauli_rotations_per_step']}",
        f"- onsite ZZ rotations per step: {resources['onsite_zz_rotations_per_step']}",
        f"- max JW string weight: {resources['max_jw_string_weight']}",
        f"- rough CNOT ladder count per step: {resources['rough_cnot_ladder_count_per_step']}",
        f"- rough CNOT ladder count total: {resources['rough_cnot_ladder_count_total']}",
        "",
        "Claim boundary: this resource estimate is intentionally conservative and not hardware-routed. A real 2D hardware path needs a separate fermionic routing/fSWAP compilation step.",
        "",
    ]
    md_path.write_text("\n".join(lines))
    return md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a separate 2D cuprate Hubbard pipeline.")
    parser.add_argument("--lx", type=int, default=6)
    parser.add_argument("--ly", type=int, default=6)
    parser.add_argument("--holes", type=int)
    parser.add_argument("--doping", type=float, default=0.125)
    parser.add_argument("--U-over-t", type=float, default=8.0)
    parser.add_argument("--t-prime-over-t", type=float, default=-0.25)
    parser.add_argument("--hopping-t", type=float, default=1.0)
    parser.add_argument("--mu", type=float, default=0.0)
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--dt", type=float, default=0.1)
    parser.add_argument("--boundary-x", choices=["open", "periodic"], default="open")
    parser.add_argument("--boundary-y", choices=["open", "periodic"], default="open")
    parser.add_argument("--initial-state", choices=["stripe_neel", "center_neel"], default="stripe_neel")
    parser.add_argument("--shots", type=int, default=20_000)
    parser.add_argument("--outdir", type=Path, default=Path("results_cuprate_2d/latest"))
    return parser.parse_args()


def config_from_args(args: argparse.Namespace) -> Cuprate2DConfig:
    sites = int(args.lx) * int(args.ly)
    holes = int(args.holes) if args.holes is not None else int(round(float(args.doping) * sites))
    return Cuprate2DConfig(
        lx=int(args.lx),
        ly=int(args.ly),
        holes=holes,
        hopping_t=float(args.hopping_t),
        t_prime_over_t=float(args.t_prime_over_t),
        u_over_t=float(args.U_over_t),
        chemical_potential=float(args.mu),
        steps=int(args.steps),
        dt=float(args.dt),
        boundary_x=str(args.boundary_x),
        boundary_y=str(args.boundary_y),
        initial_state=str(args.initial_state),
        shots=int(args.shots),
    )


def main() -> None:
    args = parse_args()
    cfg = config_from_args(args)
    validate_config(cfg)

    outdir = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    rows = initial_site_rows(cfg)
    bonds = all_hopping_bonds(cfg)
    resources = resource_estimate(cfg, bonds)
    plan = observable_plan(cfg, bonds)

    config_path = outdir / "cuprate_2d_config.json"
    modes_path = outdir / "cuprate_2d_mode_order.json"
    initial_csv = outdir / "cuprate_2d_initial_state.csv"
    bonds_csv = outdir / "cuprate_2d_bonds.csv"
    resources_json = outdir / "cuprate_2d_resource_estimate.json"
    resources_csv = outdir / "cuprate_2d_hopping_terms.csv"
    observables_json = outdir / "cuprate_2d_observable_plan.json"
    observables_csv = outdir / "cuprate_2d_observable_plan.csv"
    preview_path = outdir / "cuprate_2d_initial_state.png"

    config_path.write_text(json.dumps(asdict(cfg), indent=2) + "\n")
    modes_path.write_text(json.dumps(mode_order(cfg), indent=2) + "\n")
    write_csv(initial_csv, rows)
    write_csv(bonds_csv, bonds)
    resources_json.write_text(json.dumps(resources, indent=2) + "\n")
    write_csv(resources_csv, resources["hopping_terms"])
    observables_json.write_text(json.dumps(plan, indent=2) + "\n")
    write_observable_flat_csv(observables_csv, plan)
    preview_artifact = write_initial_state_plot(preview_path, cfg, rows)
    refs_json, refs_md = write_reference_targets(outdir)

    artifacts = {
        "config": config_path,
        "mode order": modes_path,
        "initial state CSV": initial_csv,
        "bond list": bonds_csv,
        "resource estimate JSON": resources_json,
        "hopping terms CSV": resources_csv,
        "observable plan JSON": observables_json,
        "observable plan CSV": observables_csv,
        "reference targets JSON": refs_json,
        "reference targets report": refs_md,
        "initial state preview": preview_artifact,
    }
    report = write_report(outdir, cfg, bonds, resources, artifacts)
    print(report)


if __name__ == "__main__":
    main()
