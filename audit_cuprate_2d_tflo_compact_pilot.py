"""Audit the compact proposal and read-only budget report; never submit."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

from prepare_cuprate_2d_tflo_compact_pilot import (
    BASE, RESULTS, ORIGINAL, ORIGINAL_HASH, OPTIMIZED_HASH,
    DESTINATION, analysis_protocol, classical_predictions, digest, read, save,
    validate_records, verify_tree,
)

BUDGET = RESULTS / 'tflo_compact_budget_2026-09-05'
AUDIT = RESULTS / 'tflo_compact_review_2026-09-05'


def audit(output=AUDIT):
    output = Path(output)
    if output.exists():
        raise FileExistsError('Never overwrite a completed review')
    hashes_checked = verify_tree(DESTINATION) + verify_tree(BUDGET)
    plan, budget = read(DESTINATION / 'manifest.json'), read(BUDGET / 'budget_preflight.json')
    validate_records(plan)
    checks = []

    def check(name, passed):
        checks.append({'name': name, 'passed': bool(passed)})
        if not passed:
            raise ValueError('Audit failed: ' + name)

    check('original_plan_unchanged', digest(ORIGINAL / 'manifest.json') == ORIGINAL_HASH)
    check('original_lock_unchanged', digest(ORIGINAL / 'submission_attempt.json') == plan['provenance']['old_submission_lock_sha256'])
    check('optimized_QPY_exact_copy', digest(DESTINATION / 'twirled_sampler_templates.qpy') == OPTIMIZED_HASH)
    check('proposal_unsubmitted', not (DESTINATION / 'submission_attempt.json').exists())
    check('no_authorization', plan['budget']['new_submission_authorized'] is False and budget['new_submission_authorized'] is False)
    check('new_proposed_cap_5', plan['budget']['proposed_max_execution_time_seconds'] == budget['max_execution_time_seconds'] == 5)
    check('same_backend', plan['backend_candidate'] == budget['backend'] == 'ibm_phoenix')
    check('same_plan_hash', budget['plan_sha256'] == digest(DESTINATION / 'manifest.json'))
    check('preflight_passed', budget['status'] == 'READ_ONLY_PREFLIGHT_COMPLETE_NO_JOB_SUBMITTED' and all(c['passed'] for c in budget['checks']))
    check('preflight_source_unchanged', budget['source_sha256'] == digest(BASE / 'preflight_cuprate_2d_tflo_budget.py'))
    check('no_QPU_used', budget['QPU_seconds_used_for_this_check'] == 0)
    check('allocation_unchanged', budget['circuits'] == 80 and budget['settings'] == 10 and budget['total_shots_including_calibration'] == 5120)
    check('protocol_frozen', read(DESTINATION / 'analysis_protocol.json') == analysis_protocol())
    check('classical_control_frozen', read(DESTINATION / 'classical_control_predictions.json') == classical_predictions(plan['settings']))
    local = read(DESTINATION / 'verification.json')
    check('local_checks_passed', local['checks_passed'] == 448 and all(c['passed'] for c in local['checks']))
    options = read(BUDGET / 'proposed_sampler_options.json')
    check('options_cap_and_shots', options['max_execution_time'] == 5 and options['default_shots'] == 64)
    check('no_extra_mitigation', options['twirling'] == {'enable_gates': False, 'enable_measure': False} and options['dynamical_decoupling']['enable'] is False)
    timing = read(BUDGET / 'timing_by_record.json')
    total = sum(r['shots'] * (r['aligned_duration_seconds'] + r['reset_seconds'] + r['rep_delay_seconds']) for r in timing)
    check('independent_timing_sum', abs(total - budget['execution_plus_reset_and_rep_delay_seconds']) < 1e-12)
    check('positive_finite_timing', np.isfinite(total) and total > 0)
    for scenario in budget['overhead_scenarios']:
        check('overhead_scenario_' + str(scenario['sub_jobs']),
              abs(scenario['estimated_seconds'] - (2 * scenario['sub_jobs'] + total)) < 1e-12)
    two = next(s for s in budget['overhead_scenarios'] if s['sub_jobs'] == 2)
    check('conservative_two_subjob_screen', two['estimated_seconds'] < 5)
    snapshot = read(BUDGET / 'backend_timing_snapshot.json')
    check('default_rep_delay_preserved', options['execution']['rep_delay'] == snapshot['default_rep_delay_seconds'])
    test_run = subprocess.run([sys.executable, '-m', 'unittest', '-v',
        'test_cuprate_2d_tflo_compact_pilot', 'test_cuprate_2d_tflo_refinement'],
        cwd=BASE, capture_output=True, text=True, timeout=120)
    check('offline_unit_tests', test_run.returncode == 0)
    output.mkdir(parents=True, exist_ok=False)
    transcript = test_run.stdout + test_run.stderr
    with (output / 'unit_tests.txt').open('x', encoding='utf-8') as handle:
        handle.write(transcript)
    save(output / 'verification.json', {'passed': True, 'checks_passed': len(checks),
        'checks': checks, 'frozen_artifact_hashes_verified': hashes_checked,
        'plan_sha256': digest(DESTINATION / 'manifest.json'),
        'budget_sha256': digest(BUDGET / 'budget_preflight.json'),
        'source_sha256': digest(__file__), 'unit_test_exit_code': test_run.returncode,
        'new_QPU_seconds': 0, 'new_submission_authorized': False})
    rows = ''.join(f"| {r['sub_jobs']} | {r['estimated_seconds']:.3f} s |\n" for r in budget['overhead_scenarios'])
    report = ('# Volgende compacte TFLO-pilot: klaar voor budgettoestemming\n\n'
        '**Nog niet ingediend; extra QPU-verbruik 0 seconden.**\n\n'
        'Voorstel: precies een job op ibm_phoenix, max_execution_time=5, '
        '80 circuits x 64 shots = 5120 totaal; 512 per instelling inclusief kalibratie. '
        'Geen sessie, batch, automatische retry, backendwissel of extra PEC/ZNE-kalibratie.\n\n'
        'De 42.4% X/SX-reductie is lokaal geverifieerd. De circuits houden 1008 CZ-gates; '
        'deze opschoning bewijst nog geen lagere hardwarefout. Model, mapping, '
        'tijdstippen, twirlseeds, meetvolgorde en shots zijn gelijk aan de vorige pilot.\n\n'
        '## Actuele read-only controle\n\n'
        f"Gecontroleerd op {budget['captured_utc']}; backend operationeel, "
        f"{snapshot['pending_jobs_at_capture']} wachtende jobs op dat moment. "
        f"Alle 80 circuits ISA-compatibel; {budget['checks_passed']} preflightchecks geslaagd.\n\n"
        f'Shotuitvoering inclusief reset en standaard rep_delay: {total:.6f} s. '
        'De rest van de raming komt vooral van interne opstartoverhead.\n\n'
        '| Interne subjobs | Raming inclusief overhead |\n|---|---:|\n' + rows + '\n'
        'Het aantal interne subjobs is niet vooraf bekend. Dit is een lokale scenarioanalyse, '
        'geen providerprijsopgave of garantie dat de job onder 5 s voltooit. '
        'De voorgestelde limiet kan tot afbreken leiden; al gebruikte tijd kan meetellen. '
        '[IBM workload usage](https://quantum.cloud.ibm.com/docs/en/guides/estimate-job-run-time), '
        '[uitvoeringstijdlimiet](https://quantum.cloud.ibm.com/docs/en/guides/max-execution-time).\n\n'
        '## Vooraf vastgelegde analyse\n\n'
        'Tolerantie 1 is nu vast; geen nieuwe filterselectie. Minimum 32 behouden shots per instelling, '
        'ridge 0.001, uitsluitend zes nieuwe U=0-trainingspunten in de fit. '
        'Twee U=0-validatiepunten en beide U=8-doelen blijven buiten de fit. '
        'De oorspronkelijke strikte analyse en oude gegevens blijven ongewijzigd.\n\n'
        'Verplichte vergelijking met raw, filter-only en de vooraf opgeslagen goedkope klassieke '
        'U=0-voorspelling. Primair: gepoolde Pauli-MSE op beide U=8-tijden, met 400 paired '
        'twirl/shot-bootstrapreplicaties en nieuwe U=0-fits. Geen extra winstclaim wanneer het '
        'betreffende 95%-interval nul bevat. Te weinig samples: primaire analyse stopt, zonder '
        'filterverruiming of herhaling.\n\n'
        '## Verificatie en bewaard materiaal\n\n'
        f"448 voorbereidingschecks, 80 bound-QPY-roundtrips, {budget['checks_passed']} live preflightchecks "
        f'en {len(checks)} afsluitende controles geslaagd. '
        'De eerder uitgevoerde 138 ideale-equivalentiechecks zijn via hun hashes geverifieerd; '
        'geen nieuwe statevectorrun. Alle huidige tests staan in unit_tests.txt.\n\n'
        'Reproduceerbare uitgevoerde test:\n\n'
        '```text\npython -m unittest -v test_cuprate_2d_tflo_compact_pilot test_cuprate_2d_tflo_refinement\n'
        + transcript.strip() + '\n```\n\n'
        'Deze kleine klassiek oplosbare pilot toetst meetkwaliteit, geen quantum advantage. '
        'Een vergelijking met de vorige hardwarejob blijft beschrijvend door mogelijke drift. '
        'Verdere hardwareuitvoering vraagt nieuwe expliciete toestemming en een eigen '
        'exactly-once-beveiliging. De oude runner blijft afgesloten voor herhaling.\n')
    with (output / 'NEXT_STEP_REPORT.md').open('x', encoding='utf-8') as handle:
        handle.write(report)
    shutil.copyfile(__file__, output / Path(__file__).name)
    save(output / 'sha256.json', {p.name: digest(p) for p in sorted(output.iterdir()) if p.is_file()})
    verify_tree(output)
    print(json.dumps({'status': 'READY_FOR_NEW_AUTHORIZATION_NOT_SUBMITTED',
        'audit_checks_passed': len(checks), 'preflight_checks_passed': budget['checks_passed'],
        'execution_seconds': total, 'two_subjob_estimate_seconds': two['estimated_seconds'],
        'new_QPU_seconds': 0, 'report': str(output / 'NEXT_STEP_REPORT.md')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outdir', type=Path, default=AUDIT)
    audit(parser.parse_args().outdir)
