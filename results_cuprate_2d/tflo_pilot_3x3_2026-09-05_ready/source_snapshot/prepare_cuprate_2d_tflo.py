"""Prepare and verify an OFFLINE 3x3 TFLO pilot; no submit command exists."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
from qiskit import qpy
from threadpoolctl import threadpool_limits

from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_fermionic_mapping import build_network
from cuprate_2d_fermionic_pilot import simulator_state
from validate_cuprate_2d_fermionic_dynamics import phase_distance
from cuprate_2d_tflo import (parameterized_network, compile_template, bind, skeleton,
    explicit_twirl, embed_measurement, flo_reference, initial_occupations,
    pauli_samples, physical_observables, write_json)


def state_paulis(state, width):
    indices = np.arange(2**width, dtype=np.uint32)
    bits = ((indices[:, None] >> np.arange(width)) & 1).astype(np.uint8)
    return np.abs(state)**2 @ pauli_samples(bits)


def reference_symmetries(cfg, references):
    """Conservative diagnostic: only initial-state-preserving spatial D4.

    Check exact finite-step reference grid before considering any averaging.
    These are NOT proofs of full circuit symmetry or of transfer to new times.
    """
    n = cfg.lx
    if cfg.ly != n or cfg.boundary_x != 'open' or cfg.boundary_y != 'open':
        return []
    occupations = initial_occupations(cfg).reshape(-1, 2)
    transforms = [('identity', lambda x,y:(x,y)), ('x_reflection',lambda x,y:(n-1-x,y)),
                  ('y_reflection',lambda x,y:(x,n-1-y)), ('rotation180',lambda x,y:(n-1-x,n-1-y)),
                  ('transpose',lambda x,y:(y,x)), ('anti_transpose',lambda x,y:(n-1-y,n-1-x)),
                  ('rotation90',lambda x,y:(n-1-y,x)), ('rotation270',lambda x,y:(y,n-1-x))]
    rows = []
    for name, transform in transforms:
        sites = []
        for site in range(cfg.sites):
            x, y = transform(site % n, site // n)
            sites.append(y*n+x)
        if not np.array_equal(occupations, occupations[sites]):
            continue
        permutation = [2*s+spin for s in sites for spin in (0,1)] + [cfg.qubits+s for s in sites]
        error = max(float(np.max(np.abs(np.asarray(r)-np.asarray(r)[permutation]))) for r in references)
        rows.append({'name': name, 'pauli_permutation': permutation,
                     'max_reference_grid_discrepancy': error,
                     'grid_invariant_at_1e-10': error < 1e-10,
                     'automatically_applied': False})
    return rows


def prepare(root, previous):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    cfg = Cuprate2DConfig(lx=3, ly=3, holes=1, steps=2, dt=.1, shots=512)
    checks = []
    def check(name, value, limit=1e-9):
        row = {'name': name, 'value': float(value), 'limit': limit,
               'passed': bool(np.isfinite(value) and value <= limit)}
        checks.append(row)
        write_json(root/'validation.json', {'passed': all(c['passed'] for c in checks), 'checks': checks})
        print(json.dumps(row), flush=True)
        if not row['passed']:
            raise AssertionError(name)

    def save_qpy_checked(name, circuits):
        originals = circuits if isinstance(circuits,list) else [circuits]
        with (root/name).open('wb') as handle:
            qpy.dump(originals,handle)
        with (root/name).open('rb') as handle:
            restored = qpy.load(handle)
        check(name+'_roundtrip_count',abs(len(originals)-len(restored)),0)
        for i,(before,after) in enumerate(zip(originals,restored)):
            check(name+f'_roundtrip_exact_{i}',int(before!=after),0)

    previous = Path(previous)
    prior = json.loads((previous/'plan.json').read_text())
    backend = json.loads((previous/'backend_snapshot.json').read_text())
    layout = prior['initial_layout']
    edges = {tuple(sorted(e)) for e in backend['coupling_edges']}
    check('archived_path_edges', sum(tuple(sorted((a,b))) not in edges for a,b in zip(layout,layout[1:])), 0)
    logical = parameterized_network(cfg)
    native = compile_template(logical)
    base_signature = skeleton(native)
    check('all_CZ_basis_operations', sum(i.operation.name not in ('rz','sx','x','cz') for i in native.data), 0)
    check('all_native_two_qubit_gates_adjacent', sum(len(i.qubits)==2 and abs(native.find_bit(i.qubits[0]).index-native.find_bit(i.qubits[1]).index)!=1 for i in native.data), 0)
    save_qpy_checked('logical_template.qpy',logical)
    save_qpy_checked('native_template.qpy',native)
    settings = []
    for role, u, times in [('train',0.,[0.,.1,.2,.3,.4,.5]),
                           ('flo_holdout',0.,[.15,.35]),
                           ('interacting_holdout',8.,[.2,.4])]:
        for total_time in times:
            sid = f'{role}_U{u:g}_T{total_time:g}'
            circuit = bind(native, cfg, total_time, u)
            check(sid+'_fixed_native_structure', int(skeleton(circuit) != base_signature), 0)
            state = simulator_state(circuit)
            check(sid+'_norm', abs(np.vdot(state,state).real-1))
            paulis = state_paulis(state, cfg.qubits)
            values = physical_observables(paulis)
            check(sid+'_charge_conserved', abs(values[:,0].sum()-cfg.electrons))
            check(sid+'_spin_conserved', abs(values[:,1].sum()))
            legacy = (bind(logical,cfg,0.,u) if total_time == 0
                      else build_network(replace(cfg,dt=total_time/cfg.steps,u_over_t=u)))
            check(sid+'_same_legacy_unitary_on_initial_state', phase_distance(state,simulator_state(legacy)))
            if u == 0:
                reference, covariance = flo_reference(cfg, total_time)
                check(sid+'_FLO_vs_full_statevector', np.max(np.abs(reference-paulis)))
                check(sid+'_FLO_projector', np.max(np.abs(covariance@covariance-covariance)))
            else:
                reference = paulis
                np.savez_compressed(root/f'{sid}_reference_state.npz', statevector=state)
            settings.append({'id': sid, 'role': role, 'time': total_time, 'u_over_t': u,
                             'reference': reference.tolist(),
                             'reference_kind': 'exact_FLO_finite_circuit' if u == 0 else 'exact_statevector_finite_circuit'})

    n_twirls, shots_per_twirl = 8, 64
    templates, records = [], []
    for twirl in range(n_twirls):
        seed = 202609050+twirl
        active, mask = explicit_twirl(native, seed)
        # Remove terminal measurement mask only for the state-equivalence check.
        unmasked = active.copy()
        for q in np.flatnonzero(mask):
            unmasked.x(int(q))
        check(f'twirl_{twirl}_unitary_equivalence',
              phase_distance(simulator_state(bind(unmasked,cfg,.2,8.)),
                             simulator_state(bind(native,cfg,.2,8.))))
        hardware = embed_measurement(active, layout, backend['num_qubits'])
        templates.append(hardware)
        # The same twirl seed/template is deliberately paired across settings.
        for setting in settings:
            record = {'setting_id': setting['id'], 'twirl_id': twirl, 'template_index': twirl,
                      'seed': seed, 'shots': shots_per_twirl,
                      'readout_mask_little_endian': mask.tolist(),
                      'parameter_values': {'step_time': setting['time']/cfg.steps,
                       'interaction_phase': setting['u_over_t']*cfg.hopping_t*setting['time']/cfg.steps}}
            records.append(record)
    # Interleave settings; each exact sequence is archived, not auto-submitted.
    order = np.random.default_rng(905).permutation(len(records))
    records = [records[int(i)] for i in order]
    save_qpy_checked('twirled_sampler_templates.qpy',templates)
    for template in templates:
        check('measurement_map_'+str(template.metadata['twirl_seed']),
              sum(template.find_bit(i.qubits[0]).index != layout[template.find_bit(i.clbits[0]).index]
                  for i in template.data if i.operation.name == 'measure'), 0)

    manifest = {'schema': 'tflo-plan-v1', 'status': 'OFFLINE_PREPARED_NOT_SUBMITTED',
        'config': asdict(cfg), 'backend_candidate': prior['backend'],
        'backend_calibration_source': str(previous/'backend_snapshot.json'),
        'live_backend_verified': False, 'initial_layout': layout,
        'native_operations': dict(native.count_ops()), 'native_depth': native.depth(),
        'native_structure_sha256': base_signature, 'settings': settings, 'records': records,
        'sampling': {'settings': len(settings), 'twirls_per_setting': n_twirls,
                     'shots_per_twirl': shots_per_twirl, 'shots_per_setting': 512,
                     'total_shots_including_calibration': len(records)*shots_per_twirl},
        'budget': {'existing_user_cap_seconds': 5, 'new_submission_authorized': False,
                   'provider_runtime_estimate_seconds': None,
                   'warning': 'Calibration is included in total shots. Not established to fit 5 seconds. No automatic retry or submission.'},
        'analysis_policy': {'training_U': 0., 'target_U': 8., 'sector_tolerance': 0,
                            'minimum_retained_shots_per_setting': 32,
                            'ridge_fixed_before_hardware_data': .001,
                            'bootstrap': 'paired twirl-block resampling, then shots within blocks',
                            'uncertainty_excludes_transfer_bias': True,
                            'clip_unphysical_estimates': False,
                            'symmetry_averaging_enabled': False,
                            'MESR_enabled': False, 'GPR_enabled': False,
                            'dynamical_decoupling_enabled': False},
        'symmetry_diagnostics': reference_symmetries(cfg, [s['reference'] for s in settings]),
        'method_boundary': 'Prototype TFLO + sector filter; not the full paper mitigation stack, not demonstrated hardware improvement.',
        'reference_url': 'https://arxiv.org/abs/2510.26845v2',
        'elapsed_local_seconds': time.perf_counter()-started}
    write_json(root/'manifest.json', manifest)
    source = Path(__file__).parent
    snapshot = root/'source_snapshot'
    snapshot.mkdir()
    source_names = ['cuprate_2d_tflo.py', Path(__file__).name, 'test_cuprate_2d_tflo.py',
                    'analyze_cuprate_2d_tflo.py',
                    'cuprate_2d_hubbard_pipeline.py', 'cuprate_2d_fermionic_mapping.py',
                    'cuprate_2d_fermionic_dynamics.py', 'cuprate_2d_fermionic_pilot.py',
                    'validate_cuprate_2d_fermionic_dynamics.py']
    for name in source_names:
        (snapshot/name).write_bytes((source/name).read_bytes())
    summary = (f'# TFLO 3x3: offline voorbereiding\n\n'
        f'Geen QPU-job ingediend. Geen nieuwe QPU-kosten. Bestaande cap: 5 seconden.\n\n'
        f'- Volledig t-t-prime-U model, 18 qubits, 2 vaste stappen.\n'
        f'- {len(checks)}/{len(checks)} lokale controles geslaagd.\n'
        f'- Vast native circuit: {native.count_ops().get("cz",0)} CZ, diepte {native.depth()}.\n'
        f'- 6 U=0 trainingstijden, 2 aparte U=0 validatietijden, 2 U=8 validatiepunten.\n'
        f'- 8 expliciete twirls x 64 shots = 512 per instelling; totaal 5120 geplande shots.\n'
        f'- De 5120 shots zijn inclusief kalibratie, maar passen niet aantoonbaar binnen 5 seconden.\n\n'
        f'## Verificatie\n\nExacte FLO-covariantie vergeleken met onafhankelijke volledige '
        f'Aer-statevector; native en oude logische circuits vergeleken; norm, spin/charge, '
        f'twirls en klassieke meetmap gecontroleerd. Werkelijke numerieke uitkomsten staan '
        f'in validation.json. De referentie is de eindige productformule, niet exacte H-dynamica.\n\n'
        f'## Grenzen\n\nDe fit mag alleen U=0 trainingsdata zien. U=8 referenties zijn uitsluitend '
        f'voor validatie. De zwakke vaste ridge is niet de drietrapsregularisatie uit het paper. '
        f'Symmetrieen zijn alleen gediagnosticeerd, nog niet toegepast. MESR, GPR en DD ontbreken. '
        f'Bootstrap dekt geen U-afhankelijke transferbias. Er zijn geen nieuwe hardwarebitstrings.\n\n'
        f'Bitstring-interface gecontroleerd tegen IBM-documentatie: '
        f'https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.primitives.BitArray .\n\n'
        f'Volgende hardwarestap vereist actuele backend- en kostencontrole, een expliciet '
        f'goedgekeurd totaalbudget, behoud van gate-structuur in providerinputs en een '
        f'Sampler-run die alle ruwe bitstrings per twirl archiveert.\n')
    (root/'README.md').write_text(summary, encoding='utf-8')
    hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(root.rglob('*')) if p.is_file()}
    write_json(root/'sha256.json', hashes)
    print(json.dumps({'status': manifest['status'], 'checks': len(checks),
                      'native_cz': native.count_ops().get('cz',0), 'local_seconds': time.perf_counter()-started}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outdir', required=True)
    parser.add_argument('--previous', default='results_cuprate_2d/fermionic_pilot_3x3_2026-09-05')
    args = parser.parse_args()
    with threadpool_limits(limits=1):
        prepare(args.outdir, args.previous)
