"""One bounded CPU-only chi=64 continuation; never modify the frozen kernel."""
import argparse
from dataclasses import asdict
import io
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import time
import unittest

# Apply before numpy/quimb imports, also in the supervising process.
for _key in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
             'NUMBA_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'BLIS_NUM_THREADS']:
    os.environ[_key] = '1'
os.environ['CUDA_VISIBLE_DEVICES'] = ''
import numpy as np
import psutil
from threadpoolctl import threadpool_info, threadpool_limits
import benchmark_fermionic_6x6_mps as b

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results_cuprate_2d/classical_full_6x6_mps_T04_chi64_v1'
BASE = b.OUT
HARDWARE = ROOT / 'results_cuprate_2d/hardware_readout_cz_folding_6x6_2026-09-06'
PROFILE = '6x6_chi64_threads1'
KERNEL_LIMIT = 600.0
PROCESS_LIMIT = 650.0
RSS_LIMIT = 2 * 1024**3
POLL_SECONDS = 0.1
NEW_SOURCES = ['continue_fermionic_6x6_chi64.py',
               'test_continue_fermionic_6x6_chi64.py', 'CLASSICAL_6X6_CHI64_PROTOCOL.md']


def write_once(path, value):
    """Exclusive creation makes a completed/partial run non-retryable."""
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def check_existing():
    original = b.verify_plan(BASE)
    for name, digest in b.files.read(BASE / 'sha256.json').items():
        if b.files.digest(BASE / name) != digest:
            raise ValueError('Original classical archive changed: ' + name)
    hardware = b.files.read(HARDWARE / 'plan.json')
    expected = asdict(b.cfg_for(6))
    if original['config'] != expected or hardware['config'] != expected:
        raise ValueError('Classical/hardware target configuration differs')
    for name, digest in original['input_sha256'].items():
        if name in hardware['input_sha256'] and hardware['input_sha256'][name] != digest:
            raise ValueError('Shared hardware/classical source hash differs: ' + name)
    for threads in [1, 3]:
        result = b.files.read(BASE / f'6x6_chi32_threads{threads}' / 'result.json')
        if result['status'] != 'COMPLETE' or result['config'] != expected:
            raise ValueError('Missing compatible chi32 comparison')
    return original


def check_frozen():
    plan = b.files.read(OUT / 'plan.json')
    for name, digest in plan['input_sha256'].items():
        if b.files.digest(ROOT / name) != digest:
            raise ValueError('Frozen continuation input changed: ' + name)
    return plan


def limit_reason(process_elapsed, kernel_elapsed, rss):
    if rss > RSS_LIMIT:
        return 'RSS_LIMIT'
    if process_elapsed > PROCESS_LIMIT:
        return 'PROCESS_TIMEOUT'
    if kernel_elapsed is not None and kernel_elapsed > KERNEL_LIMIT:
        return 'KERNEL_TIMEOUT'
    return None


def difference(left, right):
    delta = np.asarray(left['physical_means']) - np.asarray(right['physical_means'])
    if delta.shape != (36, 3) or not np.isfinite(delta).all():
        raise ValueError('Expected finite full 36-site observables')
    rms = np.sqrt(np.mean(delta**2, axis=0))
    maxima = np.max(np.abs(delta), axis=0)
    return {'signed_site_differences_charge_spin_doublon': delta.tolist(),
            'rms_charge_spin_doublon': rms.tolist(),
            'max_abs_charge_spin_doublon': maxima.tolist(),
            'heuristic_screen_pass': bool(np.all(rms <= .01) and maxima[1] <= .03
                                          and abs(left['number_error']) <= .01)}


def worker():
    check_frozen()
    folder = OUT / PROFILE
    folder.mkdir()  # Refuse any previous partial or completed worker.
    start = time.perf_counter()
    write_once(folder / 'kernel_started.json', {'monotonic_seconds': start, 'pid': os.getpid()})

    def alarm_handler(signum, frame):
        raise TimeoutError('600-second kernel wall-clock alarm')

    def progress(row):
        with (folder / 'progress.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(row) + '\n')
        print(json.dumps({'chi': 64, 'threads': 1, **row}), flush=True)

    previous_handler = signal.signal(signal.SIGALRM, alarm_handler)
    signal.setitimer(signal.ITIMER_REAL, KERNEL_LIMIT)
    try:
        with threadpool_limits(limits=1):
            psi, result = b.evolve(b.cfg_for(6), 64, deadline=start + KERNEL_LIMIT,
                                   progress=progress)
            if time.perf_counter() - start > KERNEL_LIMIT:
                raise TimeoutError('Kernel deadline after return')
            signal.setitimer(signal.ITIMER_REAL, 0)
            write_once(folder / 'kernel_finished.json', {'monotonic_seconds': time.perf_counter()})
            result.update(threads=1, threadpools=threadpool_info(),
                          quimb=b.quimb.__version__, numpy=np.__version__,
                          measured_with_concurrent_local_work=True,
                          isolated_performance_benchmark=False,
                          kernel_source_sha256=b.files.digest(Path(b.__file__)))
            if any(pool['num_threads'] != 1 for pool in result['threadpools']):
                raise RuntimeError('A numerical thread pool is not single-threaded')
            write_once(folder / 'result.json', result)
            np.savez_compressed(folder / 'mps_arrays.npz',
                                **{f'site_{i}': a for i, a in enumerate(psi.arrays)})
            write_once(folder / 'mps_metadata.json', {'shape': 'lrp', 'L': 72,
                       'tensor_inds': [list(t.inds) for t in psi.tensors],
                       'note': 'Original Quimb array order; axis labels saved per tensor.'})
            print(json.dumps({'status': 'COMPLETE', 'kernel_seconds': result['kernel_seconds'],
                              'number_error': result['number_error']}), flush=True)
    except (TimeoutError, MemoryError) as exc:
        write_once(folder / 'INCOMPLETE.json', {'status': 'INCOMPLETE',
                   'error_type': type(exc).__name__, 'elapsed_seconds': time.perf_counter() - start,
                   'no_final_estimate': True, 'automatic_retry': False})
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


def supervise():
    """Poll and terminate only this Popen child; no system-wide process cleanup."""
    started = time.perf_counter()
    max_rss = 0
    stop = None
    folder = OUT / PROFILE
    with (OUT / 'worker_stdout_stderr.txt').open('x', encoding='utf-8') as stream:
        process = subprocess.Popen([sys.executable, '-B', str(Path(__file__)), 'worker'],
                                   env=dict(os.environ), stdout=stream, stderr=subprocess.STDOUT)
        owned = psutil.Process(process.pid)
        kernel_start = None
        try:
            while process.poll() is None:
                now = time.perf_counter()
                try:
                    rss = owned.memory_info().rss
                except psutil.NoSuchProcess:
                    break
                max_rss = max(max_rss, rss)
                marker = folder / 'kernel_started.json'
                if kernel_start is None and marker.exists():
                    try:
                        kernel_start = b.files.read(marker)['monotonic_seconds']
                    except json.JSONDecodeError:
                        pass  # Exclusive marker creation may still be writing.
                running_kernel = kernel_start is not None and not (folder / 'kernel_finished.json').exists()
                stop = limit_reason(now - started, now - kernel_start if running_kernel else None, rss)
                if stop:
                    process.kill()
                    break
                time.sleep(POLL_SECONDS)
            returncode = process.wait(timeout=10)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
    timing = {'returncode': returncode, 'cold_worker_seconds': time.perf_counter() - started,
              'peak_polled_rss_bytes': max_rss, 'poll_interval_seconds': POLL_SECONDS,
              'stop_reason': stop, 'includes_imports': True,
              'includes_Windows_WSL_launcher': False,
              'measured_with_concurrent_local_work': True,
              'isolated_performance_benchmark': False, 'only_owned_child_terminated': bool(stop)}
    write_once(OUT / 'process_timing.json', timing)
    return returncode == 0 and (folder / 'result.json').exists(), timing


def summarize(complete, timing):
    check_frozen()
    check_existing()
    summary = {'status': 'COMPLETE' if complete else 'INCOMPLETE',
               'certified_6x6_error_bound': False, 'automatic_retry': False,
               'chi128_performed': False, 'qpu_seconds_used': 0, 'process_timing': timing}
    one = b.files.read(BASE / '6x6_chi32_threads1/result.json')
    three = b.files.read(BASE / '6x6_chi32_threads3/result.json')
    summary['chi32_threads1_minus_threads3'] = difference(one, three)
    lines = ['# Full 6x6 chi=64 continuation', '',
             'One CPU-only run. Concurrent local work: timing is not isolated.',
             'Same finite-step fermionic circuit as the existing 6x6 hardware job.', '']
    if complete:
        result = b.files.read(OUT / PROFILE / 'result.json')
        summary['result'] = result
        comparisons = {f'chi64_minus_chi32_threads{threads}': difference(result, previous)
                       for threads, previous in [(1, one), (3, three)]}
        summary['comparisons'] = comparisons
        lines += [f"Kernel time: {result['kernel_seconds']:.6f} s; cold worker: {timing['cold_worker_seconds']:.6f} s.",
                  f"Total number: {result['number_expectation']:.12g}; error from 32: {result['number_error']:.6g}.",
                  f"Log retained norm: {result['log_retained_norm']:.9g} (not a fidelity/error bound).", '',
                  '| Comparison | RMS charge | RMS spin | RMS doublon | Max charge | Max spin | Max doublon |',
                  '|---|---:|---:|---:|---:|---:|---:|']
        for name, row in comparisons.items():
            values = row['rms_charge_spin_doublon'] + row['max_abs_charge_spin_doublon']
            lines.append('| ' + name + ' | ' + ' | '.join(f'{x:.9g}' for x in values) + ' |')
        lines += ['', 'All signed site differences and thread-sensitivity comparisons are in summary.json.']
    else:
        lines += ['The bounded run did not complete. No final physical estimate is accepted.',
                  'A timeout/resource stop is not evidence that all classical methods fail.']
    lines += ['', 'A single chi=32 -> 64 difference is not a certified convergence/error bound.',
              'This does not establish that chi=64 is exact or chi=128 is required/sufficient.',
              'No shot noise applies; truncation, roundoff/thread dependence and discretization remain distinct.',
              'No quantum-advantage or matched-accuracy claim follows from these times alone.', '']
    write_once(OUT / 'summary.json', summary)
    with (OUT / 'REPORT.md').open('x', encoding='utf-8') as stream:
        stream.write('\n'.join(lines))
    write_once(OUT / 'sha256.json', {str(path.relative_to(OUT)): b.files.digest(path)
               for path in sorted(OUT.rglob('*')) if path.is_file()})
    print(json.dumps({k: v for k, v in summary.items() if k not in ['result', 'comparisons',
          'chi32_threads1_minus_threads3']}), flush=True)


def driver():
    if OUT.exists():
        raise FileExistsError('Refuse repeat/overwrite of canonical chi64 continuation')
    check_existing()
    OUT.mkdir()
    snapshots = OUT / 'source_snapshot'
    snapshots.mkdir()
    names = sorted(set(NEW_SOURCES + b.SOURCES))
    for name in names:
        shutil.copyfile(ROOT / name, snapshots / name)
    inputs = names + [str(path.relative_to(ROOT)) for path in
        [BASE / 'plan.json', BASE / 'summary.json', BASE / 'sha256.json', HARDWARE / 'plan.json',
         BASE / '6x6_chi32_threads1/result.json', BASE / '6x6_chi32_threads3/result.json']]
    plan = {'schema': 'full6x6-chi64-bounded-v1', 'config': asdict(b.cfg_for(6)),
            'chi': 64, 'threads': 1, 'kernel_seconds_limit': KERNEL_LIMIT,
            'process_seconds_limit': PROCESS_LIMIT, 'rss_limit_bytes': RSS_LIMIT,
            'rss_guard_is_polled': True, 'poll_seconds': POLL_SECONDS,
            'automatic_retry': False, 'chi128_authorized': False, 'qpu_seconds_used': 0,
            'python': platform.python_version(), 'quimb': b.quimb.__version__, 'numpy': np.__version__,
            'wsl_cpus': os.cpu_count(), 'affinity': sorted(os.sched_getaffinity(0)),
            'wsl_ram_bytes': psutil.virtual_memory().total,
            'measured_with_concurrent_local_work': True, 'isolated_performance_benchmark': False,
            'input_sha256': {name: b.files.digest(ROOT / name) for name in inputs}}
    write_once(OUT / 'plan.json', plan)
    log = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromNames(
        ['test_benchmark_fermionic_6x6_mps', 'test_continue_fermionic_6x6_chi64'])
    with threadpool_limits(limits=1):
        tests = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    with (OUT / 'unit_tests.txt').open('x', encoding='utf-8') as stream:
        stream.write(log.getvalue())
    if not tests.wasSuccessful():
        raise AssertionError(log.getvalue())
    print(json.dumps({'unit_tests_pass': tests.testsRun, 'stage': 'chi64_one_thread_started',
                      'limits_kernel_process_seconds': [KERNEL_LIMIT, PROCESS_LIMIT]}), flush=True)
    complete, timing = supervise()
    summarize(complete, timing)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['run', 'worker'])
    args = parser.parse_args()
    if args.stage == 'run':
        driver()
    else:
        worker()
