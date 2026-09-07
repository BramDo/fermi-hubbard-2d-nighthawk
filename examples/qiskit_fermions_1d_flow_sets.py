"""Run the qiskit-fermions 1D Hubbard flow-set tutorial end to end.

This is the spinless, open-chain tutorial model

    H = -t sum_j (a^dagger_j a_{j+1} + h.c.) + U sum_j n_j n_{j+1},

not the spinful onsite-interaction Hubbard model used by the production 2D
cuprate workflow in this repository.

The implementation follows the tagged qiskit-fermions 0.1.0 guide:
https://github.com/Qiskit/qiskit-fermions/blob/0.1.0/docs/guides/1d_fermi_hubbard.rst

Reported two-qubit depths are logical pre-routing depths. Flow sets remove
intra-group Trotter error, but splitting the three noncommuting groups still
introduces inter-group product-formula error.
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
from collections import defaultdict
from importlib.metadata import version
from pathlib import Path

import numpy as np
from qiskit.circuit import QuantumCircuit, QuantumRegister
from qiskit.passmanager import MultiStagePassManager
from qiskit.quantum_info import Operator, SparseObservable, SparsePauliOp, Statevector
from qiskit.synthesis import LieTrotter
from qiskit.synthesis.evolution import EvolutionSynthesis
from qiskit_fermions.circuit import FermionicCircuit
from qiskit_fermions.circuit.library import Evolution
from qiskit_fermions.mappers import map_transfer_vertex_generators
from qiskit_fermions.mappers.library import jordan_wigner, transfer_vertex_to_fermion
from qiskit_fermions.operators import TransferVertexOperator
from qiskit_fermions.transpiler import FermionicCircuitToDAG, QuantumDAGToCircuit
from qiskit_fermions.transpiler.passes import (
    CustomF2QLayout,
    F2QSynthesis,
    MapperFnEvolutionSynthesis,
)
from scipy.linalg import expm


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "results_qiskit_fermions" / "flow_sets_1d"


def fermi_hubbard_1d(
    num_sites: int, tunneling: float, interaction: float
) -> TransferVertexOperator:
    """Build the spinless nearest-neighbor tutorial Hamiltonian."""
    data: defaultdict[tuple[tuple[int, int], ...], complex] = defaultdict(complex)
    for j in range(num_sites - 1):
        k = j + 1
        data[((j, k),)] += tunneling
        data[((k, j),)] += tunneling
        data[()] += interaction / 4
        data[((j, j),)] -= interaction / 4
        data[((k, k),)] -= interaction / 4
        data[((j, j), (k, k))] += interaction / 4
    return TransferVertexOperator.from_dict(data)


def flow_set_groups(operator: TransferVertexOperator) -> list[int]:
    """Assign east hopping, west hopping, and diagonal terms to three groups."""
    groups = []
    for terms, _ in operator.iter_terms():
        match terms:
            case [(left, right)] if right == left + 1:
                groups.append(0)
            case [(left, right)] if right == left - 1:
                groups.append(1)
            case _:
                groups.append(2)
    return groups


def flow_set_action(action: tuple[int, int], num_qubits: int) -> SparseObservable:
    """Map one transfer/vertex generator into the domain-wall encoding."""
    match action:
        case (j, k) if j == k:
            return SparseObservable.from_sparse_list(
                [("ZZ", [j, j + 1], 1.0)], num_qubits=num_qubits
            )
        case (j, k) if k == j + 1:
            return SparseObservable.from_sparse_list(
                [("X", [k], -0.5)], num_qubits=num_qubits
            )
        case (j, k) if k == j - 1:
            return SparseObservable.from_sparse_list(
                [("ZXZ", [k, k + 1, k + 2], 0.5)], num_qubits=num_qubits
            )
        case _:
            raise ValueError(f"not a nearest-neighbor transfer operator: {action}")


def flow_set_encoding(
    operator: TransferVertexOperator, num_qubits: int
) -> SparseObservable:
    """Map a transfer/vertex operator into the domain-wall encoding."""
    return map_transfer_vertex_generators(
        operator,
        lambda action: flow_set_action(action, num_qubits),
        identity=lambda: SparseObservable.identity(num_qubits),
        compose=SparseObservable.compose,
    ).simplify()


def domain_wall_bits(occupations: list[int]) -> list[int]:
    """Convert little-endian occupations to cumulative-parity bits."""
    parity = 0
    bits = [0]
    for occupation in occupations:
        parity ^= occupation
        bits.append(parity)
    return bits


def domain_wall_isometry(num_sites: int) -> np.ndarray:
    """Return the isometry from Jordan-Wigner to domain-wall basis states."""
    isometry = np.zeros((2 ** (num_sites + 1), 2**num_sites), dtype=complex)
    for index in range(2**num_sites):
        occupations = [(index >> j) & 1 for j in range(num_sites)]
        bits = domain_wall_bits(occupations)
        isometry[sum(bit << j for j, bit in enumerate(bits)), index] = 1.0
    return isometry


def to_matrix(observable: SparseObservable) -> np.ndarray:
    """Convert a SparseObservable to a dense matrix for small-system checks."""
    return SparsePauliOp.from_sparse_observable(observable).to_matrix()


def flow_set_pass_manager(mode_register, product_formula=None) -> MultiStagePassManager:
    """Map a fermionic register with the one-ancilla domain-wall encoding."""
    synthesis = F2QSynthesis()
    synthesis.methods["Evolution"] = MapperFnEvolutionSynthesis(
        flow_set_encoding, product_formula=product_formula
    )
    qubit_register = QuantumRegister(mode_register.size + 1, "q")
    return MultiStagePassManager(
        input=FermionicCircuitToDAG(),
        layout=CustomF2QLayout({mode_register: qubit_register}),
        synthesis=synthesis,
        output=QuantumDAGToCircuit(),
    )


def cz_brickwork(circuit: QuantumCircuit) -> None:
    """Emit an overlapping CZ chain in two parallel layers."""
    for offset in (0, 1):
        for j in range(offset, circuit.num_qubits - 1, 2):
            circuit.cz(j, j + 1)


def rzz_layers(circuit: QuantumCircuit, angles: dict[tuple[int, int], float]) -> None:
    """Emit nearest- and next-nearest-neighbor RZZ gates in four layers."""
    near = [(j, k) for j, k in angles if k - j == 1]
    far = [(j, k) for j, k in angles if k - j == 2]
    schedule = [
        [(j, k) for j, k in near if j % 2 == 0],
        [(j, k) for j, k in far if j % 4 in (0, 1)],
        [(j, k) for j, k in near if j % 2 == 1],
        [(j, k) for j, k in far if j % 4 in (2, 3)],
    ]
    for layer in schedule:
        for j, k in layer:
            circuit.rzz(angles[j, k], j, k)


class FlowSetSynthesis(EvolutionSynthesis):
    """Synthesize the three encoded flow-set shapes used by this tutorial."""

    preserve_order = True

    def __init__(self, reps: int = 1):
        self.reps = reps

    def synthesize(self, evolution) -> QuantumCircuit:
        circuit = QuantumCircuit(evolution.operator.num_qubits)
        east: list[tuple[int, float]] = []
        west: list[tuple[int, float]] = []
        diagonal: dict[tuple[int, int], float] = {}

        for label, indices, coeff in evolution.operator.to_sparse_list():
            angle = 2 * evolution.time * coeff.real / self.reps
            match label, indices:
                case "", _:
                    circuit.global_phase -= self.reps * angle / 2
                case "X", [qubit]:
                    east.append((qubit, angle))
                case "ZXZ", [j, k, l] if (k, l) == (j + 1, j + 2):
                    west.append((k, angle))
                case "ZZ", [j, k]:
                    diagonal[min(j, k), max(j, k)] = angle
                case _:
                    raise ValueError(f"unexpected Pauli term: {label} on {indices}")

        for _ in range(self.reps):
            for qubit, angle in east:
                circuit.rx(angle, qubit)
            if west:
                cz_brickwork(circuit)
                for qubit, angle in west:
                    circuit.rx(angle, qubit)
                cz_brickwork(circuit)
            rzz_layers(circuit, diagonal)
        return circuit


class _Evolution:
    """Minimal container used to test a synthesis against exact exponentiation."""

    def __init__(self, operator: SparseObservable, time: float):
        self.operator = operator
        self.time = time


def max_abs(array: np.ndarray) -> float:
    return float(np.max(np.abs(array)))


def two_qubit_depth(circuit: QuantumCircuit) -> int:
    return int(circuit.depth(lambda instruction: len(instruction.qubits) == 2))


def flow_set_exact_error(num_sites: int, time: float = 0.37) -> float:
    """Return the worst group-wise unitary error, modulo global phase."""
    operator = fermi_hubbard_1d(num_sites, tunneling=1.0, interaction=2.0)
    operator.groups = flow_set_groups(operator)
    worst = 0.0
    for group in operator.split_out_groups():
        encoded = flow_set_encoding(group, num_sites + 1)
        if not encoded.to_sparse_list():
            continue
        synthesized = FlowSetSynthesis().synthesize(_Evolution(encoded, time))
        exact = expm(-1j * time * to_matrix(encoded))
        got = Operator(synthesized).data
        pivot = np.unravel_index(np.argmax(np.abs(exact)), exact.shape)
        phase = exact[pivot] / got[pivot]
        worst = max(worst, max_abs(got * phase - exact))
    return worst


def evolution_stats(
    num_sites: int, product_formula, total_time: float
) -> dict[str, int]:
    """Compile one grouped Trotter step and report entangling cost."""
    operator = fermi_hubbard_1d(num_sites, tunneling=1.0, interaction=2.0)
    operator.groups = flow_set_groups(operator)
    circuit = FermionicCircuit(num_sites)
    circuit.append(Evolution(num_sites, operator, time=total_time), circuit.modes)
    grouped = circuit.decompose()
    compiled = flow_set_pass_manager(grouped.register, product_formula).run(grouped)
    decomposed = compiled.decompose(reps=6)
    return {
        "two_qubit_depth": two_qubit_depth(decomposed),
        "cx_count": int(decomposed.count_ops().get("cx", 0)),
    }


def trotter_metrics(
    circuit: FermionicCircuit,
    product_formula,
    initial_label: str,
    reference: np.ndarray,
) -> dict[str, float | int]:
    """Compare one synthesis to exact evolution of the encoded Hamiltonian."""
    compiled = flow_set_pass_manager(circuit.register, product_formula).run(circuit)
    decomposed = compiled.decompose(reps=6)
    evolved = Statevector.from_label(initial_label).evolve(decomposed)
    fidelity = abs(np.vdot(evolved.data, reference)) ** 2
    return {
        "fidelity": float(fidelity),
        "cx_count": int(decomposed.count_ops().get("cx", 0)),
        "two_qubit_depth": two_qubit_depth(decomposed),
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"artifact directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    num_sites = 4
    num_qubits = num_sites + 1
    tunneling = 1.0
    interaction = 2.0
    total_time = 1.0
    occupations = [1, 0, 1, 0]

    hamiltonian = fermi_hubbard_1d(num_sites, tunneling, interaction)
    hamiltonian.groups = flow_set_groups(hamiltonian)
    term_count = sum(1 for _ in hamiltonian.iter_terms())
    group_weights = [
        sorted(
            {
                len(indices)
                for _, indices, _ in flow_set_encoding(group, num_qubits).to_sparse_list()
            }
        )
        for group in hamiltonian.split_out_groups()
    ]

    encoded = flow_set_encoding(hamiltonian, num_qubits)
    isometry = domain_wall_isometry(num_sites)
    jw_matrix = to_matrix(
        jordan_wigner(transfer_vertex_to_fermion(hamiltonian), num_sites).simplify()
    )
    flow_matrix = to_matrix(encoded)
    orthonormality_error = max_abs(
        isometry.conj().T @ isometry - np.eye(2**num_sites)
    )
    intertwining_error = max_abs(flow_matrix @ isometry - isometry @ jw_matrix)
    jw_spectrum = np.linalg.eigvalsh(jw_matrix)
    flow_spectrum = np.linalg.eigvalsh(flow_matrix)
    doubled_spectrum = np.sort(np.concatenate([jw_spectrum, jw_spectrum]))
    spectrum_error = max_abs(np.sort(flow_spectrum) - doubled_spectrum)

    circuit = FermionicCircuit(num_sites)
    circuit.append(Evolution(num_sites, hamiltonian, time=total_time), circuit.modes)
    grouped_circuit = circuit.decompose()

    default_compiled = flow_set_pass_manager(grouped_circuit.register).run(grouped_circuit)
    default_decomposed = default_compiled.decompose(reps=6)
    grouped_lie = {
        "cx_count": int(default_decomposed.count_ops().get("cx", 0)),
        "two_qubit_depth": two_qubit_depth(default_decomposed),
    }

    flow_compiled = flow_set_pass_manager(
        grouped_circuit.register, FlowSetSynthesis()
    ).run(grouped_circuit)
    flow_decomposed = flow_compiled.decompose(reps=6)
    grouped_flow = {
        "cx_count": int(flow_decomposed.count_ops().get("cx", 0)),
        "two_qubit_depth": two_qubit_depth(flow_decomposed),
    }

    scaling_rows = []
    for sites in (4, 10, 20, 50, 100):
        flow_stats = evolution_stats(sites, FlowSetSynthesis(), total_time)
        lie_stats = evolution_stats(sites, LieTrotter(), total_time)
        scaling_rows.append(
            {
                "num_sites": sites,
                "flow_two_qubit_depth": flow_stats["two_qubit_depth"],
                "flow_cx_count": flow_stats["cx_count"],
                "lie_two_qubit_depth": lie_stats["two_qubit_depth"],
                "lie_cx_count": lie_stats["cx_count"],
            }
        )

    exactness_rows = [
        {"num_sites": sites, "max_unitary_error": flow_set_exact_error(sites)}
        for sites in (4, 6)
    ]

    initial_label = "".join(str(bit) for bit in reversed(domain_wall_bits(occupations)))
    reference = (
        expm(-1j * total_time * flow_matrix)
        @ Statevector.from_label(initial_label).data
    )
    trotter_rows = []
    for steps in (1, 2, 4, 8):
        flow_metrics = trotter_metrics(
            circuit, FlowSetSynthesis(reps=steps), initial_label, reference
        )
        lie_metrics = trotter_metrics(
            circuit, LieTrotter(reps=steps), initial_label, reference
        )
        trotter_rows.append(
            {
                "steps": steps,
                "flow_fidelity": flow_metrics["fidelity"],
                "flow_cx_count": flow_metrics["cx_count"],
                "flow_two_qubit_depth": flow_metrics["two_qubit_depth"],
                "lie_fidelity": lie_metrics["fidelity"],
                "lie_cx_count": lie_metrics["cx_count"],
                "lie_two_qubit_depth": lie_metrics["two_qubit_depth"],
            }
        )

    density_time = 0.8
    state_jw = np.zeros(2**num_sites, dtype=complex)
    state_jw[sum(value << j for j, value in enumerate(occupations))] = 1.0
    evolved_jw = expm(-1j * density_time * jw_matrix) @ state_jw
    evolved_flow = expm(-1j * density_time * flow_matrix) @ (isometry @ state_jw)
    density_rows = []
    for site in range(num_sites):
        v_flow = to_matrix(
            SparseObservable.from_sparse_list(
                [("ZZ", [site, site + 1], 1.0)], num_qubits=num_qubits
            )
        )
        v_jw = to_matrix(
            SparseObservable.from_sparse_list(
                [("Z", [site], 1.0)], num_qubits=num_sites
            )
        )
        density_flow = (
            1 - np.vdot(evolved_flow, v_flow @ evolved_flow).real
        ) / 2
        density_jw = (1 - np.vdot(evolved_jw, v_jw @ evolved_jw).real) / 2
        density_rows.append(
            {
                "site": site,
                "flow_density": float(density_flow),
                "jw_density": float(density_jw),
                "absolute_difference": float(abs(density_flow - density_jw)),
            }
        )

    checks = {
        "hamiltonian_has_14_terms": term_count == 14,
        "three_flow_groups": hamiltonian.num_groups() == 3,
        "expected_group_weights": group_weights == [[1], [3], [0, 2]],
        "isometry_is_orthonormal": orthonormality_error < 1e-12,
        "encoding_intertwines_jw": intertwining_error < 1e-12,
        "encoded_spectrum_is_doubled_jw": spectrum_error < 1e-10,
        "flow_groups_are_synthesized_exactly": max(
            row["max_unitary_error"] for row in exactness_rows
        )
        < 1e-9,
        "flow_two_qubit_depth_is_constant_12": {
            row["flow_two_qubit_depth"] for row in scaling_rows
        }
        == {12},
        "flow_fidelity_exceeds_lie": all(
            row["flow_fidelity"] > row["lie_fidelity"] for row in trotter_rows
        ),
        "eight_step_flow_fidelity_exceeds_0p99": trotter_rows[-1][
            "flow_fidelity"
        ]
        > 0.99,
        "site_densities_match_jw": max(
            row["absolute_difference"] for row in density_rows
        )
        < 1e-10,
    }
    all_passed = all(checks.values())

    summary = {
        "status": "PASS" if all_passed else "FAIL",
        "environment": {
            "python": platform.python_version(),
            "qiskit": version("qiskit"),
            "qiskit_fermions": version("qiskit-fermions"),
        },
        "model": {
            "description": "spinless open 1D chain with nearest-neighbor density interaction",
            "num_sites": num_sites,
            "num_qubits": num_qubits,
            "tunneling": tunneling,
            "interaction": interaction,
            "initial_occupations": occupations,
            "domain_wall_label": initial_label,
        },
        "claim_boundaries": [
            "This is not the spinful onsite-interaction Hubbard model used by the 2D cuprate workflow.",
            "Circuit depths are logical pre-routing depths and do not include hardware-connectivity overhead.",
            "Flow-set synthesis is exact within each group; finite-step inter-group Trotter error remains.",
            "Dense exact matrix checks are limited to small chains.",
        ],
        "operator": {
            "term_count": term_count,
            "group_count": hamiltonian.num_groups(),
            "group_pauli_weights": group_weights,
            "ground_energy_jw": float(jw_spectrum[0]),
            "ground_energy_flow": float(flow_spectrum[0]),
        },
        "encoding_verification": {
            "orthonormality_max_error": orthonormality_error,
            "intertwining_max_error": intertwining_error,
            "spectrum_max_error": spectrum_error,
        },
        "four_site_grouped_circuit": {
            "default_lie_trotter": grouped_lie,
            "flow_set_synthesis": grouped_flow,
        },
        "flow_group_exactness": exactness_rows,
        "scaling": scaling_rows,
        "trotter_comparison": trotter_rows,
        "site_densities_at_t_0p8": density_rows,
        "checks": checks,
    }

    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    write_csv(output_dir / "depth_scaling.csv", scaling_rows)
    write_csv(output_dir / "trotter_comparison.csv", trotter_rows)
    write_csv(output_dir / "site_densities_t0p8.csv", density_rows)

    print(f"qiskit-fermions 1D flow-set example: {summary['status']}")
    print(
        f"Hamiltonian: {term_count} terms, {hamiltonian.num_groups()} groups, "
        f"weights {group_weights}"
    )
    print(
        "Encoding errors: "
        f"orthonormality={orthonormality_error:.3e}, "
        f"intertwining={intertwining_error:.3e}, spectrum={spectrum_error:.3e}"
    )
    print(
        "Four-site grouped circuit: "
        f"Lie {grouped_lie['cx_count']} CX/depth {grouped_lie['two_qubit_depth']}; "
        f"flow {grouped_flow['cx_count']} CX/depth {grouped_flow['two_qubit_depth']}"
    )
    for row in trotter_rows:
        print(
            f"{row['steps']} step(s): flow fidelity {row['flow_fidelity']:.6f} "
            f"({row['flow_cx_count']} CX, depth {row['flow_two_qubit_depth']}); "
            f"Lie {row['lie_fidelity']:.6f} "
            f"({row['lie_cx_count']} CX, depth {row['lie_two_qubit_depth']})"
        )
    print(f"Artifacts: {output_dir}")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
