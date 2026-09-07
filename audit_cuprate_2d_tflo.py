"""Read-only bundle audit and local unit tests; writes a separate audit folder."""
import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import qiskit
from qiskit import qpy

from cuprate_2d_tflo import skeleton, write_json


def audit(root, destination):
    root, destination = Path(root), Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    hashes = json.loads((root/'sha256.json').read_text())
    checks = []
    def check(name, passed):
        checks.append({'name':name,'passed':bool(passed)})
        if not passed:
            write_json(destination/'failed_checks.json',checks)
            raise AssertionError(name)
    for name, expected in hashes.items():
        target = (root/name).resolve()
        check('safe_path_'+name,target.is_relative_to(root.resolve()))
        check('sha256_'+name,hashlib.sha256(target.read_bytes()).hexdigest()==expected)
    manifest = json.loads((root/'manifest.json').read_text())
    validation = json.loads((root/'validation.json').read_text())
    check('exact_validation',validation['passed'] and all(c['passed'] for c in validation['checks']))
    with (root/'native_template.qpy').open('rb') as handle:
        native = qpy.load(handle)[0]
    check('qpy_native_signature',skeleton(native)==manifest['native_structure_sha256'])
    check('qpy_native_operations',dict(native.count_ops())==manifest['native_operations'])
    with (root/'twirled_sampler_templates.qpy').open('rb') as handle:
        templates = qpy.load(handle)
    check('eight_twirl_templates',len(templates)==8)
    settings = {s['id']:s for s in manifest['settings']}
    seen = set()
    for r in manifest['records']:
        key = (r['setting_id'],r['twirl_id'])
        check('unique_'+str(key),key not in seen)
        seen.add(key)
        template = templates[r['template_index']]
        check('mask_'+str(key),template.metadata['readout_mask_little_endian']==r['readout_mask_little_endian'])
        check('seed_'+str(key),template.metadata['twirl_seed']==r['seed'])
        setting = settings[r['setting_id']]
        values = r['parameter_values']
        check('time_'+str(key),np.isclose(values['step_time'],setting['time']/manifest['config']['steps']))
        check('U_'+str(key),np.isclose(values['interaction_phase'],setting['u_over_t']*manifest['config']['hopping_t']*values['step_time']))
        bound = template.assign_parameters({p:values[p.name] for p in template.parameters})
        check('all_parameters_bound_'+str(key),bound.num_parameters==0)
        check('preserved_twirl_skeleton_'+str(key),skeleton(bound)==skeleton(template))
        check('CZ_exposure_'+str(key),bound.count_ops()['cz']==native.count_ops()['cz'])
    check('complete_settings',len(seen)==len(settings)*len(templates))
    check('total_shots',sum(r['shots'] for r in manifest['records'])==5120)
    check('no_submission_authority',not manifest['budget']['new_submission_authorized'])
    source = Path(__file__).parent
    command = [sys.executable,str(source/'test_cuprate_2d_tflo.py')]
    tests = subprocess.run(command,cwd=source,capture_output=True,text=True,timeout=180)
    (destination/'unit_tests.txt').write_text(tests.stdout+tests.stderr,encoding='utf-8')
    check('unit_tests',tests.returncode==0)
    maxima = {suffix:max(c['value'] for c in validation['checks'] if c['name'].endswith(suffix))
              for suffix in ('FLO_vs_full_statevector','same_legacy_unitary_on_initial_state','unitary_equivalence')}
    result = {'passed':True,'plan_dir':str(root),'audit_checks':len(checks),'checks':checks,
              'physics_checks':len(validation['checks']),'maxima':maxima,
              'unit_test_command':command,'unit_test_exit_code':tests.returncode,
              'versions':{'python':platform.python_version(),'qiskit':qiskit.__version__,'numpy':np.__version__},
              'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
                 [source/name for name in ('cuprate_2d_tflo.py','prepare_cuprate_2d_tflo.py',
                   'test_cuprate_2d_tflo.py','analyze_cuprate_2d_tflo.py','audit_cuprate_2d_tflo.py')]},
              'hardware_improvement_demonstrated':False,'new_QPU_seconds':0}
    write_json(destination/'verification.json',result)
    report = ('# TFLO 3x3 verification\n\n'
        f"Passed: {len(checks)} archive checks and {len(validation['checks'])} exact-physics checks.\n\n"
        f"Full local unit-test output: unit_tests.txt; exit code {tests.returncode}.\n\n"
        f"Largest FLO/full-statevector difference: {maxima['FLO_vs_full_statevector']:.3e}.\n"
        f"Native template: {native.count_ops()['cz']} CZ; depth {native.depth()}.\n\n"
        'All 80 planned setting/twirl records retain their compiled structure after binding. '
        'The two-spin sector filter, TFLO fit, raw Sampler archive, hierarchical bootstrap '
        'and held-out-reference leakage tests ran locally. Synthetic readout errors in tests '
        'are not a calibrated Phoenix noise model. No hardware improvement is claimed.\n\n'
        'Budget: 512 shots per setting, 5120 including calibration and holdouts. '
        'No QPU job submitted; not established to fit the existing 5-second cap.\n\n'
        'Symmetry averaging remains disabled because nontrivial physical symmetries are '
        'not exact on the finite-step reference grid. MESR, GPR and DD are not implemented '
        'in this prototype. The fixed ridge prior is not the paper\'s learned regularizer.\n')
    (destination/'VERIFICATION.md').write_text(report,encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('checks','source_sha256')}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan-dir',required=True)
    parser.add_argument('--outdir',required=True)
    args=parser.parse_args()
    audit(args.plan_dir,args.outdir)
