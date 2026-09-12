"""Clean project-source compilation and transitive audit; stdlib only, no QPU.

Install the pinned Lean toolchain and Mathlib cache first, then:
    python3 verify.py --workers 2
Every invocation uses a new empty output directory. No previous project
object file is accepted as input. Upstream dependency caches are allowed.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import argparse, datetime, hashlib, json, os, re, shutil, subprocess, time

HERE = Path(__file__).resolve().parent
PILOT = ['AnalyticPilot', 'SparsePilot', 'CoefficientPilot', 'MatrixPilot',
         'ProjectionPilot', 'MomentPilot', 'DynamicsPilot']
ALLOWED = {'propext', 'Classical.choice', 'Quot.sound'}

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def strip_comments(code):
    # Preserve newlines; correctly handle nested Lean block comments.
    out, i, level = [], 0, 0
    while i < len(code):
        if code[i:i+2] == '/-':
            level += 1
            i += 2
        elif level and code[i:i+2] == '-/':
            level -= 1
            i += 2
        elif not level and code[i:i+2] == '--':
            j = code.find('\n', i)
            i = len(code) if j < 0 else j
        else:
            out.append(code[i] if not level or code[i] == '\n' else ' ')
            i += 1
    assert level == 0
    return ''.join(out)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=2)
    parser.add_argument('--memory-mb', type=int, default=4000)
    parser.add_argument('--timeout', type=int, default=900, help='per module, seconds')
    args = parser.parse_args()
    assert 1 <= args.workers <= 4 and args.memory_mb >= 1000
    lake = shutil.which('lake')
    lean = shutil.which('lean')
    assert lake and lean, 'Install Lean via elan and put lake/lean on PATH.'
    manifest = json.loads((HERE / 'source-manifest.json').read_text())
    modules = manifest['modules']
    for relative, digest in manifest['files'].items():
        assert sha(HERE / relative) == digest, 'Package file differs: ' + relative
    sources = {name: HERE / (name + '.lean') for name in modules}
    dependencies, names = {}, {}
    for name, source in sources.items():
        text = strip_comments(source.read_text())
        assert not re.search(r'\b(sorry|admit|axiom|native_decide|bv_decide|allowUnsafeReducibility)\b', text), name
        dependencies[name] = set(re.findall(r'^import\s+(\S+)', text, re.M)) & sources.keys()
        ns = re.search(r'^namespace\s+(\w+)', text, re.M)
        assert ns, name
        names[name] = [ns.group(1) + '.' + n for n in re.findall(r'^theorem\s+(\w+)', text, re.M)]
    pilot_names = [n for mod in PILOT for n in names[mod]]
    assert len(pilot_names) == 66
    lock = json.loads((HERE / 'lake-manifest.json').read_text())
    version = subprocess.check_output([lean, '--version'], cwd=HERE, text=True).strip()
    assert 'version 4.33.1,' in version, version
    upstream = {}
    for spec in lock['packages']:
        folder = HERE / '.lake/packages' / spec['name']
        actual = subprocess.check_output(['git', '-C', str(folder), 'rev-parse', 'HEAD'], text=True).strip()
        assert actual == spec['rev'], spec['name']
        upstream[spec['name']] = actual
    paths = subprocess.check_output([lake, 'env', 'printenv', 'LEAN_PATH'], cwd=HERE, text=True).strip()
    # Reject local build-cache paths. Only pinned upstream packages and the new
    # empty output directory below may resolve project imports.
    upstream_paths = []
    for item in paths.split(os.pathsep):
        p = Path(item)
        p = p if p.is_absolute() else HERE / p
        if '.lake/packages/' in p.as_posix():
            upstream_paths.append(str(p))
    assert upstream_paths, 'No pinned dependency library paths found.'
    out = HERE / '.verification' / datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    build = out / 'compiled'
    build.mkdir(parents=True)
    env = dict(os.environ, LEAN_PATH=os.pathsep.join([str(build)] + upstream_paths))
    records, completed, futures = [], set(), {}
    started = time.monotonic()

    def compile_one(name):
        tick = time.monotonic()
        cmd = [lean, '-M', str(args.memory_mb), '-j', '1', '-o', str(build / (name + '.olean')), str(sources[name])]
        with (out / (name + '.txt')).open('w') as log:
            proc = subprocess.run(cmd, cwd=HERE, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=args.timeout)
        row = {'module': name, 'exit_code': proc.returncode, 'seconds': time.monotonic()-tick,
               'source_sha256': sha(sources[name])}
        if proc.returncode:
            raise RuntimeError(name + ' failed; see ' + str(out / (name + '.txt')))
        row['olean_sha256'] = sha(build / (name + '.olean'))
        return row

    report = {'status': 'RUNNING', 'original_local_commit': manifest['original_local_commit'],
              'lean_version': version, 'upstream_revisions': upstream, 'project_modules_reused': 0,
              'source_manifest_sha256': sha(HERE / 'source-manifest.json'), 'commands': records}
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            while len(completed) < len(modules):
                for name in modules:
                    if len(futures) >= args.workers:
                        break
                    if name not in completed and name not in futures.values() and dependencies[name] <= completed:
                        futures[pool.submit(compile_one, name)] = name
                assert futures, 'Import cycle or missing dependency'
                done, _ = wait(futures, timeout=40, return_when=FIRST_COMPLETED)
                if not done:
                    print('RUNNING', sorted(futures.values()), 'completed', len(completed), flush=True)
                for future in done:
                    row = future.result()
                    completed.add(futures.pop(future))
                    records.append(row)
                    print('COMPILED', len(completed), '/', len(modules), row['module'], round(row['seconds'], 2), flush=True)
                    (out / 'progress.json').write_text(json.dumps(report, indent=2) + '\n')
        all_names = [n for mod in modules for n in names[mod]]
        assert len(all_names) == len(set(all_names))
        audit = out / 'Audit.lean'
        audit.write_text('import DynamicsPilot\n' + '\n'.join('#print axioms ' + n for n in all_names) + '\n'
                         + '#print CentralDynamics.expectation\n#print CentralDynamics.exact_expectation_hasSum\n'
                         + '#print CentralDynamics.coefficient_four\n#print CentralDynamics.exact_series_split\n')
        result = subprocess.run([lean, '-M', str(args.memory_mb), str(audit)], cwd=HERE, env=env,
                                capture_output=True, text=True, timeout=args.timeout)
        (out / 'Audit.txt').write_text(result.stdout + result.stderr)
        assert result.returncode == 0, 'Final audit compilation failed'
        found = dict(re.findall(r"'([^']+)' depends on axioms:\s*\[([^\]]*)\]", result.stdout))
        for n in re.findall(r"'([^']+)' does not depend on any axioms", result.stdout):
            found[n] = ''
        assert set(found) == set(all_names), 'Incomplete theorem audit'
        axioms = {n: [a.strip() for a in v.split(',') if a.strip()] for n, v in found.items()}
        assert all(set(v) <= ALLOWED for v in axioms.values()), 'Unapproved axiom'
        report.update(all_project_theorems=len(all_names), pilot_theorems=66, axioms=axioms)
        negatives = {
            'WrongFourth': 'example : scalarCoefficient 4 = 2 := by\n  rw [coefficient_four]\n  norm_num\n',
            'WrongSecond': 'example : scalarCoefficient 2 = 1 := by\n  rw [coefficient_two]\n  norm_num\n',
            'WrongFactor': 'example : (1024 : ℚ) / (4^4*24) = 1 := by\n  norm_num\n'}
        for name, goal in negatives.items():
            src = out / (name + '.lean')
            src.write_text('import DynamicsPilot\nopen CentralDynamics\n' + goal)
            result = subprocess.run([lean, '-M', str(args.memory_mb), str(src)], cwd=HERE, env=env,
                                    capture_output=True, text=True, timeout=120)
            (out / (name + '.txt')).write_text(result.stdout + result.stderr)
            assert result.returncode == 1 and re.search(r'is false|⊢ False', result.stdout)
        # Independent integer arithmetic requires no third-party Python packages.
        result = subprocess.run([shutil.which('python3') or 'python', '-B', 'checks/pilot/check.py'],
                                cwd=HERE, capture_output=True, text=True, timeout=120)
        (out / 'integer-check.txt').write_text(result.stdout + result.stderr)
        assert result.returncode == 0
        report.update(status='CLEAN_SOURCE_BUILD_AND_TRANSITIVE_AUDIT_PASSED',
                      negative_controls_rejected=3, certified_coefficients=['0','0','0','0','1'],
                      qpu_seconds=0, elapsed_seconds=time.monotonic()-started)
    except BaseException as exc:
        report.update(status='FAILED', error=repr(exc), elapsed_seconds=time.monotonic()-started)
        raise
    finally:
        (out / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
        (HERE / '.verification/latest.json').write_text(json.dumps({'path': str(out), 'status': report['status']}, indent=2) + '\n')
        print('VERIFICATION', report['status'], str(out), flush=True)

if __name__ == '__main__':
    main()
