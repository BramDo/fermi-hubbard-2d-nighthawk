"""Small-state review checks only; no backend or runtime service is created."""
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
from qiskit.quantum_info import Statevector
from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_qiskit_circuit import build_circuit
from cuprate_2d_tflo import parameterized_network, bind

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'publication/fermionic_review_2026-10-19_v1'


def probabilities(cfg, family):
    circuit, _ = build_circuit(cfg, measured=False, circuit_family=family)
    return Statevector.from_instruction(circuit).probabilities()


def main():
    cfg = Cuprate2DConfig(lx=2, ly=3, holes=2, steps=1, dt=.4,
                         u_over_t=8, t_prime_over_t=-.25)
    legacy = probabilities(cfg, 'number_preserving_t_only')
    legacy_u0 = probabilities(replace(cfg, u_over_t=0), 'number_preserving_t_only')
    legacy_prime0 = probabilities(replace(cfg, t_prime_over_t=0), 'number_preserving_t_only')
    full = replace(cfg, steps=2, dt=.2)
    template = parameterized_network(full)
    p8 = Statevector.from_instruction(bind(template, full, .4, 8)).probabilities()
    p0 = Statevector.from_instruction(bind(template, full, .4, 0)).probabilities()
    zero_prime = replace(full, t_prime_over_t=0)
    pp0 = Statevector.from_instruction(bind(parameterized_network(zero_prime), zero_prime, .4, 8)).probabilities()
    result = {
        'legacy_one_step_max_probability_change_U8_vs_U0': float(np.max(abs(legacy-legacy_u0))),
        'legacy_one_step_max_probability_change_tprime': float(np.max(abs(legacy-legacy_prime0))),
        'full_two_step_max_probability_change_U8_vs_U0': float(np.max(abs(p8-p0))),
        'full_two_step_max_probability_change_tprime': float(np.max(abs(p8-pp0))),
        'scope': 'Exact 2x3 ideal statevectors; not a 6x6 accuracy or convergence certificate',
        'new_qpu_seconds': 0,
    }
    assert result['legacy_one_step_max_probability_change_U8_vs_U0'] < 1e-12
    assert result['legacy_one_step_max_probability_change_tprime'] < 1e-12
    assert result['full_two_step_max_probability_change_U8_vs_U0'] > 1e-5
    assert result['full_two_step_max_probability_change_tprime'] > 1e-5
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'physics_checks.json').open('x') as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
