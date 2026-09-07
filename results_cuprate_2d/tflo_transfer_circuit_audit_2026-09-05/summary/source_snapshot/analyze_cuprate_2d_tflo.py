"""Analyze a frozen TFLO Sampler archive locally; never submits a job.

Example: python analyze_cuprate_2d_tflo.py --plan-dir RESULTS --raw RAW.json
         --out REPORT.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_tflo import (initial_occupations, decode_bitstrings, analyze)


def load_archive(plan_dir, raw_file):
    root = Path(plan_dir)
    hashes = json.loads((root/'sha256.json').read_text())
    for name, expected in hashes.items():
        target = (root/name).resolve()
        if not target.is_relative_to(root.resolve()):
            raise ValueError('Unsafe path in local hash manifest')
        if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Frozen artifact changed: {name}')
    plan = json.loads((root/'manifest.json').read_text())
    raw = json.loads(Path(raw_file).read_text())
    if plan['schema'] != 'tflo-plan-v1' or raw['schema'] != 'tflo-raw-v1':
        raise ValueError('Unsupported schema')
    cfg = Cuprate2DConfig(**plan['config'])
    if raw['width'] != cfg.qubits or not raw.get('job_id'):
        raise ValueError('Wrong width or missing provenance')
    expected_records = {(r['setting_id'],r['twirl_id']):r for r in plan['records']}
    if len(expected_records) != len(plan['records']):
        raise ValueError('Duplicate record in plan')
    if len(raw['records']) != len(expected_records):
        raise ValueError('Partial archive: not all settings and twirls were received')
    decoded, seen = {}, set()
    for record in raw['records']:
        key = (record['setting_id'],record['twirl_id'])
        if key not in expected_records or key in seen:
            raise ValueError('Unexpected or duplicate raw record')
        seen.add(key)
        expected = expected_records[key]
        if any(record.get(k) != v for k,v in expected.items()):
            raise ValueError('Raw metadata differs from the frozen plan')
        if len(record['bitstrings']) != expected['shots']:
            raise ValueError('Shot count mismatch')
        bits = decode_bitstrings(record['bitstrings'],cfg.qubits,
                                 expected['readout_mask_little_endian'])
        decoded.setdefault(key[0],{})[key[1]] = bits
    occupations = initial_occupations(cfg)
    return plan, raw, decoded, int(occupations[::2].sum()), int(occupations[1::2].sum())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan-dir',required=True)
    parser.add_argument('--raw',required=True)
    parser.add_argument('--out',required=True)
    parser.add_argument('--bootstrap',type=int,default=200)
    args = parser.parse_args()
    destination = Path(args.out)
    if destination.exists():
        raise FileExistsError('Analysis never overwrites an existing report')
    plan, raw, decoded, n_up, n_down = load_archive(args.plan_dir,args.raw)
    result = analyze(plan['settings'],decoded,n_up,n_down,
                     tolerance=plan['analysis_policy']['sector_tolerance'],
                     bootstrap=args.bootstrap)
    result.update(job_id=raw['job_id'],
                  input_sha256=hashlib.sha256(Path(args.raw).read_bytes()).hexdigest(),
                  plan_manifest_sha256=hashlib.sha256((Path(args.plan_dir)/'manifest.json').read_bytes()).hexdigest(),
                  assessment='Exploratory held-out validation, not a hardware accuracy certification.')
    with destination.open('x',encoding='utf-8') as handle:
        json.dump(result,handle,indent=2,allow_nan=False)
        handle.write('\n')
    print(json.dumps({'output':str(destination),'job_id':raw['job_id'],
                      'bootstrap_failures':result['bootstrap_failures']}))


if __name__ == '__main__':
    main()
