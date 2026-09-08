"""Write a bounded interpretation of a completed and independently checked pilot."""
from pathlib import Path
import argparse, json

def read(p): return json.loads(p.read_text())

def report(folder):
    summary=read(folder/'summary.json')
    checked=read(folder/'verification'/'verification.json')
    if checked['status']!='SAVED_PILOT_VERIFIED': raise ValueError('Verification required')
    target=folder/'DELIVERY.md'
    if target.exists(): raise FileExistsError('Preserve earlier report')
    names={
        'raw_equal_total_shots':'Raw (1536 base-noise shots)',
        'readout_equal_total_shots':'Readout only (1536 base-noise shots)',
        'zne_linear':'Readout + linear ZNE',
        'zne_richardson':'Readout + quadratic Richardson ZNE',
        'lmpf_2d_lcbp_chi1':'Readout + L-MPF, 2D LCBP, chi=1',
        'lmpf_2d_lcbp_chi1_ridge':'Readout + L-MPF, 2D LCBP, chi=1, fixed ridge',
        'lmpf_2d_lcbp_chi2':'Readout + L-MPF, 2D LCBP, chi=2',
        'lmpf_2d_lcbp_chi2_ridge':'Readout + L-MPF, 2D LCBP, chi=2, fixed ridge',
        'lmpf_2d_exact_contract_chi1':'Readout + L-MPF, exact low-chi TN contraction, chi=1',
        'lmpf_2d_exact_contract_chi2':'Readout + L-MPF, exact low-chi TN contraction, chi=2',
        'lmpf_2d_exact_contract_chi2_ridge':'Readout + L-MPF, exact low-chi TN contraction, chi=2, fixed ridge',
        'lmpf_exact_overlap_oracle':'Readout + exact-overlap L-MPF oracle (not scalable)',
        'lmpf_exact_overlap_ridge':'Readout + exact-overlap oracle, fixed ridge (not scalable)',
        'lmpf_noise_model_scale_0.7':'L-MPF oracle, model rates 30% too low',
        'lmpf_noise_model_scale_1.3':'L-MPF oracle, model rates 30% too high',
        'classical_2d_tn_chi1':'Purely classical low-chi TN, chi=1',
        'classical_2d_tn_chi2':'Purely classical low-chi TN, chi=2',
    }
    lines=['# Offline L-MPF pilot: completed with explicit rejected fits', '',
        'Date: 2026-09-08. **No new QPU job; no validated 6x6 L-MPF hardware result.**', '',
        'The project now has an executed, source-snapshotted implementation of the',
        '[L-MPF observable-overlap objective](https://arxiv.org/html/2609.05024v1).',
        'This is an independent Python implementation and a small matched-surrogate',
        'validation, not a reproduction of the authors\' 65-qubit DTC demonstration.', '',
        '## What was actually run', '',
        '- 2x2 full-fermionic Hubbard: eight qubits, N=3, U=8, t=1, t\'=-0.25,',
        '  T=0.4, two symmetric product-formula steps. Reference: ideal finite circuit.',
        '- Frozen ibm_phoenix/Nighthawk 2x4 physical subgraph; native circuit depth',
        '  1415, including 675 CZ gates. Classical block fusion did not shorten it.',
        '- Local depolarizing Lindblad surrogate derived from saved gate infidelities;',
        '  readout included. This is not a learned or validated device noise model.',
        '- Three noisy arms at scales 1,2,3, 512 shots each. Baselines use 1536',
        '  base-noise shots. Their shared samples give 2560 total simulated bitshots.',
        '- Eight Z and four onsite ZZ operators. Coefficients depend only on their',
        '  Hilbert-Schmidt overlaps, never on the initial-state target expectations.',
        '- Genuine 2D BP-gauged tensor networks at chi=1,2, four-edge loop corrections,',
        '  and an independent exact contraction of those same truncated networks.',
        '- Fixed ridge = 1/512 is a separately labelled variance safeguard.',
        '  No Clifford rescaling, ergodic amplification, or chi extrapolation.', '',
        '## Predicted total error at the stated shot budget', '',
        'Each entry is sqrt(mean(bias^2 + sampling variance)) over the four lattice',
        'sites, under the matched simulation model. Lower is better. Cross-observable',
        'correlations are retained. These are not hardware confidence intervals.', '',
        '| Method | Charge | Spin | Doublons |',
        '| --- | ---: | ---: | ---: |']
    families=['charge','spin','doublon']
    for name,label in names.items():
        if name not in summary['methods'] or name.startswith('classical_'): continue
        row=summary['methods'][name]['families']
        lines.append('| '+label+' | '+' | '.join(f"{row[f]['model_expected_rmse_with_shots']:.6f}" for f in families)+' |')
    lines+=['', '## Systematic model error, excluding finite-shot variance', '',
        'This second table separates error cancellation from shot-noise amplification.',
        'Purely classical TN estimates have no shot variance in this comparison.', '',
        '| Method | Charge | Spin | Doublons |', '| --- | ---: | ---: | ---: |']
    for name,label in names.items():
        if name not in summary['methods']: continue
        row=summary['methods'][name]['families']
        lines.append('| '+label+' | '+' | '.join(f"{row[f]['model_bias_rmse']:.6f}" for f in families)+' |')
    rejected=summary['rejected_fits']
    lines+=['', '## Rejections and verification', '',
        f"- {checked['tests_passed']} regression tests passed; all 12 saved operators were checked.",
        f"- {checked['accepted_tn_fits_checked']} accepted TN coefficient sets rechecked for normalization,",
        '  constrained optimality, and residual consistency.',
        f"- {len(rejected)} TN coefficient fits were rejected and retained in summary.json.",
        f"- BP propagation updates that missed strict convergence: {checked['bp_propagation_nonconverged_updates']}.",
        f"- Maximum saved sample reconstruction error: {checked['max_sample_reconstruction_error']:.3g}.",
        '- Forward density evolution, backward Heisenberg evolution, native routing,',
        '  bit order, fermionic circuit choice, covariance and source hashes checked.',
        '- Verification certifies these software/model consistency checks, not hardware',
        '  accuracy, tensor-network convergence, or the Hamiltonian-exponential target.', '',
        '| Rejected method | Observable index | Reason |', '| --- | ---: | --- |']
    for item in rejected:
        lines.append(f"| {item['method']} | {item['observable']} | {item['reason'].replace('|','/')} |")
    lines+=['', 'LCBP failures are not replaced silently. A complete method score is included',
        'only when all 12 coefficients exist. The separately named exact-contraction',
        'variant still truncates the operator TN at low chi, but contracts its overlaps',
        'exactly on this small graph. It is not evidence that the scalable loop',
        'approximation works on the failed cases. Inspect each operator JSON for',
        'actual loop-vs-exact errors, warnings and Gram spectra.', '',
        '## Existing 3x3 and 6x6 hardware: prepared, not mitigated with L-MPF', '',
        'The separate [hardware input summary](../lmpf_hardware_inputs_2026-09-08_v1/summary.json)',
        'preserves the real folding shots, corrects asymmetric readout before undoing',
        'X masks, and estimates conditional shot plus shared-calibration covariance.',
        'The 3x3 job is daem7r642tqs73autong; the 6x6 job is daen2vdnj4cs73afcn00.',
        'This latter job is not the later original/compact seven-second TFLO job.', '',
        'Their own validated arm-specific overlaps and a learned or independently',
        'validated noise model remain missing. CZ-only folding is not the pilot\'s',
        'all-gate noise scaling. Eight-qubit coefficients cannot be transferred to',
        '18 or 72 qubits. No historical result or timing claim was overwritten.', '',
        '## Reproducibility and evidence', '',
        f"- Full-pilot wall time: {summary['seconds']:.3f} seconds, including dense validation,",
        '  multiple TN backends, sampling and diagnostics. This is not the timing of',
        '  a production-only mitigation pass or a comparison with the 150-second 6x6 run.',
        '- [Plan and circuit/noise identity](plan.json).',
        '- [All numerical results and single-seed observed errors](summary.json).',
        '- [Independent verification](verification/verification.json).',
        '- [Input/output hashes](input_output_sha256.json); raw arm memory and native QPY.',
        '- source_snapshot contains the actually executed pilot implementation.',
        '- Earlier smoke failures and stopped/rejected pilots remain in neighbouring',
        '  dated folders; they are not accepted hardware or mitigation results.',
        '- [Protocol, conventions and limitations](../../theory/LMPF_PROTOCOL.md).', '',
        'The physics-verification workflow required preserving failed loop contractions',
        'and keeping shot uncertainty, approximation error and hardware validity separate.',
        'No quantum advantage is established by this pilot.', '']
    target.write_text('\n'.join(lines),encoding='utf-8')
    print(target)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path)
    report(p.parse_args().folder)
