"""Offline-only frozen-data mitigation comparison; no provider calls."""
from pathlib import Path
import hashlib
import json
import platform
import time
import numpy as np
from cuprate_2d_tflo import decode_bitstrings, pauli_samples, physical_observables
from analyze_hardware_6x6_rocz import predictions

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / 'results_cuprate_2d'
RUN = RESULTS / 'hardware_readout_cz_folding_6x6_2026-09-06'
CLASSICAL = RESULTS / 'classical_full_6x6_mps_T04_chi64_v1'
OUT = RESULTS / 'mitigation_6x6_sector_comparison_2026-09-06_v1'
WEIGHTS = np.array([4/3, 1/3, -2/3])
B = 2000
SEED = 202609060913


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    with path.open('x', encoding='utf-8') as file:
        json.dump(value, file, indent=2, allow_nan=False)
        file.write('\n')


def strict_success(bits, n_up=16, n_down=16):
    b = np.asarray(bits)
    if b.ndim != 2 or b.shape[1] % 2 or not np.all((b == 0) | (b == 1)):
        raise ValueError('Expected binary shots with interleaved spins')
    return (b[:, ::2].sum(axis=1) == n_up) & (b[:, 1::2].sum(axis=1) == n_down)


def site_samples(bits):
    b = np.asarray(bits, dtype=float)
    up, down = b[:, ::2], b[:, 1::2]
    return np.stack([up + down, up - down, up * down], axis=-1)


def projected(success_means, numerator_means, weights):
    den = np.tensordot(weights, success_means, axes=(0, 0))
    if not np.isfinite(den) or den <= 0:
        raise ValueError('Nonpositive or nonfinite projected denominator')
    return np.tensordot(weights, numerator_means, axes=(0, 0)) / den


def summarize(name, point, boot, reference, shots, includes_readout=False):
    diff = np.sqrt(np.mean((point - reference)**2, axis=0))
    bd = np.sqrt(np.mean((boot - reference)**2, axis=1))
    nboot = boot[:, :, 0].sum(axis=1)
    # Derive the four local probabilities without clipping.
    charge, spin, doublon = point.T
    up = (charge + spin)/2
    down = (charge - spin)/2
    local_probs = np.stack([1-charge+doublon, down-doublon,
                            up-doublon, doublon], axis=-1)
    return {
        'arm': name, 'physical_charge_spin_doublon': point.tolist(),
        'physical_pointwise_95pct_intervals': np.quantile(boot, [.025, .975], axis=0).tolist(),
        'N': float(charge.sum()), 'N_95pct_interval': np.quantile(nboot, [.025, .975]).tolist(),
        'spin_profile_rms': float(np.sqrt(np.mean(spin**2))),
        'mean_doublon': float(doublon.mean()),
        'rms_discrepancy_vs_chi64_charge_spin_doublon': diff.tolist(),
        'rms_discrepancy_95pct_intervals': np.quantile(bd, [.025, .975], axis=0).tolist(),
        'bootstrap_ci_endpoint_max_change_1000_to_2000': float(np.max(np.abs(
            np.quantile(bd[:1000], [.025, .975], axis=0) - np.quantile(bd, [.025, .975], axis=0)))),
        'minimum_onsite_probability': float(local_probs.min()),
        'physical_bounds_satisfied_at_point': bool(local_probs.min() >= -1e-12),
        'acquired_shots_including_used_calibration': shots,
        'includes_readout_inversion': includes_readout,
        'comparison_is_error_against_exact': False,
    }


def main():
    if OUT.exists():
        raise FileExistsError('Do not overwrite a completed or partial comparison')
    started = time.perf_counter()
    paths = [RUN/'plan.json', RUN/'raw_bitstrings.json', RUN/'analysis/results.json',
             RUN/'analysis/bootstrap.npz', CLASSICAL/'summary.json',
             ROOT/'cuprate_2d_tflo.py', ROOT/'analyze_hardware_6x6_rocz.py',
             ROOT/'MITIGATION_6X6_REANALYSIS_PROTOCOL.md', Path(__file__),
             ROOT/'test_compare_6x6_sector_mitigation.py']
    before = {str(p.relative_to(ROOT)): digest(p) for p in paths}
    archive_checks = 0
    for manifest in ['hardware_archive_sha256.json', 'analysis_archive_sha256.json']:
        for name, expected in read(RUN/manifest).items():
            if digest(RUN/name) != expected:
                raise ValueError('Frozen source hash mismatch: ' + name)
            archive_checks += 1
    raw, plan = read(RUN/'raw_bitstrings.json'), read(RUN/'plan.json')
    assert raw['job_id'] == 'daen2vdnj4cs73afcn00' and raw['width'] == 72
    assert len(raw['records']) == len(plan['records']) == 26
    old = read(RUN/'analysis/results.json')
    classical = read(CLASSICAL/'summary.json')
    reference = np.asarray(classical['result']['physical_means'])
    assert reference.shape == (36, 3) and not classical['certified_6x6_error_bound']
    rng = np.random.default_rng(SEED)
    means = np.empty((3, 8, 108))
    raw_boot = np.zeros((B, 36, 3))
    numerator = np.zeros((3, 36, 3)); success = np.zeros(3)
    numerator_boot = np.zeros((B, 3, 36, 3)); success_boot = np.zeros((B, 3))
    masks = np.zeros((8, 72), dtype=int)
    calibration = {}; counts = []
    independent_max = 0.; number_mismatches = 0
    seen = set()
    for rec, wanted in zip(raw['records'], plan['records']):
        assert all(rec[k] == v for k, v in wanted.items())
        assert rec['shots'] == len(rec['bitstrings']) == 512
        bits = decode_bitstrings(rec['bitstrings'], 72, rec['readout_mask_little_endian'])
        if rec['role'] == 'calibration':
            calibration[rec['state']] = bits
            continue
        f, t = rec['factor']-1, rec['twirl_id']
        assert (f, t) not in seen
        seen.add((f,t)); masks[t] = rec['readout_mask_little_endian']
        physical = site_samples(bits)
        ps = pauli_samples(bits)
        independent_max = max(independent_max, float(np.max(np.abs(physical_observables(ps)-physical))))
        means[f,t] = ps.mean(axis=0)
        keep = strict_success(bits)
        # Independent Python-integer implementation: different decoding and popcount path.
        mask_integer = sum(int(v) << i for i,v in enumerate(rec['readout_mask_little_endian']))
        up_integer_mask = sum(1 << (2*i) for i in range(36))
        down_integer_mask = up_integer_mask << 1
        keep_integer = np.array([((int(s,2)^mask_integer)&up_integer_mask).bit_count() == 16
            and ((int(s,2)^mask_integer)&down_integer_mask).bit_count() == 16 for s in rec['bitstrings']])
        number_mismatches += int(np.count_nonzero(keep != keep_integer))
        count = int(keep.sum())
        counts.append({'factor':f+1, 'twirl_id':t, 'accepted':count, 'acquired':512})
        success[f] += count/4096
        numerator[f] += physical[keep].sum(axis=0)/4096
        # Whole-shot multinomial bootstrap, including the rejected events.
        weights = rng.multinomial(512, np.full(512, 1/512), size=B)
        success_boot[:,f] += weights[:,keep].sum(axis=1)/4096
        numerator_boot[:,f] += (weights[:,keep] @ physical[keep].reshape(count,108)).reshape(B,36,3)/4096
        if f == 0:
            raw_boot += (weights @ physical.reshape(512,108)).reshape(B,36,3)/4096
    assert len(seen) == 24 and number_mismatches == 0
    failures = np.array([calibration[0].sum(axis=0), (1-calibration[1]).sum(axis=0)])
    point_old = predictions(means, masks, (failures+.5)/513)
    baseline_delta = float(np.max(np.abs(point_old-np.asarray(old['point_paulis']))))
    assert baseline_delta < 1e-12 and independent_max < 1e-12
    base_boot = np.load(RUN/'analysis/bootstrap.npz')['physical']
    arms = []
    for j in range(3):
        saved = old['arms'][j]
        arms.append(summarize(saved['arm'], np.asarray(saved['physical_charge_spin_doublon']),
            base_boot[:,j], reference, saved['shot_cost'], includes_readout=j>0))
    sector = projected(success, numerator, np.array([1.,0.,0.]))
    assert np.all(success_boot[:,0] > 0)
    sector_boot = numerator_boot[:,0]/success_boot[:,0,None,None]
    arms.append(summarize('strict_sector_factor1_no_readout_inverse',sector,sector_boot,reference,4096))
    den_zne = float(WEIGHTS @ success)
    den_boot = success_boot @ WEIGHTS
    den_ci = np.quantile(den_boot,[.025,.975])
    if den_zne <= 0 or den_ci[0] <= 0 or np.any(den_boot <= 0):
        ratio_status = 'WITHHELD_UNSTABLE_DENOMINATOR'
        zne_sector = zne_sector_boot = None
    else:
        ratio_status = 'EXPLORATORY_RATIO_FINITE_DENOMINATOR_NOT_VALIDATED'
        zne_sector = projected(success, numerator, WEIGHTS)
        zne_sector_boot = np.einsum('f,bfsc->bsc',WEIGHTS,numerator_boot)/den_boot[:,None,None]
        arms.append(summarize('cz_zne_then_sector_ratio_no_readout_inverse',zne_sector,zne_sector_boot,reference,12288))
    paired_gain = np.sqrt(np.mean((raw_boot-reference)**2,axis=1))-np.sqrt(np.mean((sector_boot-reference)**2,axis=1))
    point_gain = np.asarray(arms[0]['rms_discrepancy_vs_chi64_charge_spin_doublon'])-np.asarray(arms[3]['rms_discrepancy_vs_chi64_charge_spin_doublon'])
    gain_ci = np.quantile(paired_gain,[.025,.975],axis=0)
    summary = {
        'status':'COMPLETE_OFFLINE_EXPLORATORY_COMPARISON', 'source_job':raw['job_id'],
        'new_qpu_seconds':0, 'new_jobs_submitted':0, 'tflo_applied':False, 'dd_applied':False,
        'full_requested_stack_status':'BLOCKED_NEEDS_MATCHED_6X6_U0_HARDWARE_AND_NEW_BUDGET',
        'classical_reference_certified':False, 'quantum_advantage_demonstrated':False,
        'postselection_N32_is_enforced_not_validation':True, 'values_clipped':False,
        'bootstrap_replicates':B, 'bootstrap_seed':SEED,
        'counts_by_factor_twirl':sorted(counts,key=lambda r:(r['factor'],r['twirl_id'])),
        'accepted_by_factor':[int(round(v*4096)) for v in success],
        'acceptance_fraction_by_factor':success.tolist(),
        'zne_sector_denominator':den_zne, 'zne_sector_denominator_95pct':den_ci.tolist(),
        'zne_sector_ratio_status':ratio_status,
        'arms':arms,
        'paired_raw_minus_sector_rms_discrepancy_gain':point_gain.tolist(),
        'paired_gain_95pct_intervals':gain_ci.tolist(),
        'classical_chi32_to_chi64':classical['comparisons'],
        'uncertainty_scope':'Exploratory conditional whole-shot PUB bootstrap; old readout arms also use shared independent-channel calibration draws. Excludes drift, correlated readout, selection and extrapolation bias, MPS and Trotter error. Not equal shot budgets.',
        'seconds':time.perf_counter()-started,
    }
    checks = {
        'source_archive_hashes_verified':archive_checks,
        'baseline_reproduction_max_abs':baseline_delta,
        'independent_integer_sector_disagreements':number_mismatches,
        'independent_direct_bits_vs_pauli_max_abs':independent_max,
        'postselected_N32_max_abs':float(np.max(np.abs(sector_boot[:,:,0].sum(axis=1)-32))),
        'postselected_total_spin_max_abs':float(np.max(np.abs(sector_boot[:,:,1].sum(axis=1)))),
        'all_input_hashes_unchanged':all(digest(ROOT/p)==h for p,h in before.items()),
        'python':platform.python_version(), 'numpy':np.__version__,
    }
    assert checks['all_input_hashes_unchanged']
    assert checks['postselected_N32_max_abs'] < 1e-10
    assert checks['postselected_total_spin_max_abs'] < 1e-10
    OUT.mkdir()
    write_json(OUT/'summary.json',summary)
    write_json(OUT/'verification.json',checks)
    write_json(OUT/'input_sha256.json',before)
    np.savez_compressed(OUT/'bootstrap.npz',raw=raw_boot,strict_sector=sector_boot,
        zne_sector=np.array([]) if zne_sector_boot is None else zne_sector_boot,
        success=success_boot, numerator=numerator_boot, paired_gain=paired_gain)
    lines = ['# 6x6: extra sector-mitigatie op bestaande hardwaredata','',
        'Geen nieuwe hardwarejob: 0 extra QPU-seconden. Bronjob '+raw['job_id']+'.',
        'Dit is een verkennende heranalyse, niet de nog ontbrekende TFLO/DD-hardwaretest.','',
        '| Methode | N | RMS lading versus chi64 | RMS spin versus chi64 | RMS doublon versus chi64 |',
        '|---|---:|---:|---:|---:|']
    for a in arms:
        d=a['rms_discrepancy_vs_chi64_charge_spin_doublon']
        lines.append(f"| {a['arm']} | {a['N']:.5f} | {d[0]:.5f} | {d[1]:.5f} | {d[2]:.5f} |")
    lines += ['', '## Uitkomst en grenzen','',
        'Strikte selectie behoudt per CZ-factor 1/2/3 respectievelijk '+str(summary['accepted_by_factor'])+' van 4096 shots.',
        'N=32 en totale spin=0 zijn door dit filter afgedwongen en bewijzen geen herstelde dynamica.',
        'De sectorarmen bevatten GEEN readout-inversie. De oude readout+ZNE-arm blijft apart staan.',
        'De ratio-arm extrapoleert de ongenormaliseerde teller en noemer met vaste gewichten (4/3,1/3,-2/3).',
        'ZNE+sector noemer95%: '+str(den_ci.tolist())+'; status: '+ratio_status+'.','',
        'Gepaarde vermindering in RMS-afstand raw minus strikte selectie (lading, spin, doublon): '+str(point_gain.tolist())+'.',
        'Bijbehorende 95%-intervallen: '+str(gain_ci.tolist())+'.',
        'Een kleinere afstand tot chi64 is geen foutcertificaat: chi64 is nog niet geconvergeerd.','',
        summary['uncertainty_scope'],'',
        '## Nog nodig voor de gevraagde sterkere mitigatie','',
        'TFLO vereist passende 6x6-U=0-trainingsmetingen plus onafhankelijke holdouts. De 3x3-fit en 5x5-controle kunnen dit niet vervangen.',
        'DD is een pulsaanpassing tijdens uitvoering en kan niet achteraf aan opgeslagen shots worden toegevoegd.',
        'Nieuwe metingen uitsluitend na een verse raming en expliciete budgettoestemming; oude toestemming is verbruikt.',
        'Zie het bewaarde protocol voor een matched DD-aan/uit en TFLO-vervolgontwerp.',
        'De physics-skill leidde tot afzonderlijke armen, een onafhankelijke decodercheck en expliciete selectie-/referentiebiasgrenzen.','',
        'Bron: [Google/Phasecraft, Methods: Error mitigation](https://arxiv.org/html/2510.26845v2).','']
    (OUT/'RAPPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    (OUT/'VERIFICATION.md').write_text('# Uitgevoerde onafhankelijke controles\n\n'
        +'Uitvoer van NumPy-, integer-popcount- en SHA256-controles:\n\n```json\n'
        +json.dumps(checks,indent=2)+'\n```\n\n'
        +'Dit verifieert de rekenketen, niet hardware-accuratesse. Zie unit_tests.txt voor analytische testgevallen.\n',encoding='utf-8')
    snap=OUT/'source_snapshot'; snap.mkdir()
    for p in paths:
        if p.parent==ROOT:
            (snap/p.name).write_bytes(p.read_bytes())
    write_json(OUT/'sha256.json',{str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file()})
    print(json.dumps({'accepted':summary['accepted_by_factor'],'arms':[
        {'arm':a['arm'],'N':a['N'],'RMS':a['rms_discrepancy_vs_chi64_charge_spin_doublon']} for a in arms],
        'paired_gain_95pct':gain_ci.tolist(),'verification':checks,'seconds':summary['seconds']}),flush=True)


if __name__ == '__main__':
    main()
