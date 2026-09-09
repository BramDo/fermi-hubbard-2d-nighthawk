"""Freeze calibration-only estimator inputs before the approved hardware dispatch."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
from lmpf_2d import floor_hardware as h
def run():
    h.require(not h.LOCK.exists(),'Cannot redefine analysis after dispatch')
    plan,pubs=h.frozen()
    source=h.CANDIDATE/'forecast_inputs.json'
    h.require(h.safe.digest(source)==h.safe.read(h.CANDIDATE/'sha256.json')['forecast_inputs.json'],'Changed source Grams')
    inp=h.safe.read(source)
    payload={'schema':'frozen-floor64-hardware-analysis-v1','job_plan_sha256':h.safe.digest(h.RUN/'plan.json'),
        'method_order':['raw','readout','zne','lmpf_original','lmpf_floor'],
        'observables':[8,9,22],'physical_order':['charge','spin','D'],'central_modes':[8,9],
        'actual_target_strata_shots':[512,1024,512,512],'calibration_per_prepared_state':256,
        'floor_penalty_denominator':64,'original_penalty_denominator':512,'eta':1,
        'bootstrap_replicates':10000,'bootstrap_seed':2026090922,
        'calibration_uncertainty':'Independent Beta(K+.5,256-K+.5) per prepared state and central bit, shared across all methods.',
        'target_bootstrap':'Separate multinomial draw per each of16 target PUBs, then combine into the four fixed strata.',
        'rng_order':'Calibration Beta draws first, then target PUBs in frozen plan order.',
        'point_weights_frozen_before_target_scoring':True,'no_target_or_reference_in_fit':True,
        'grams':inp['grams'],'low_grams':inp['low_grams'],'masks':inp['masks'],
        'reference_paulis':[plan['target']['reference'][i] for i in (8,9,22)],
        'reference_scope':'Exact identical finite circuit, not automatically exact Hamiltonian exponential.',
        'same_shot_baselines':True,'clip_estimates':False,'recompute_weights_per_calibration_draw':True,
        'analysis_protocol_sha256':plan['analysis_protocol_sha256'],'source_grams_sha256':h.safe.digest(source),
        'source_sha256':h.safe.digest(__file__),'new_qpu_seconds':0}
    h.safe.exclusive_json(h.RUN/'analysis_inputs.json',payload)
    h.safe.exclusive_json(h.RUN/'analysis_contract_sha256.json',{'analysis_inputs.json':h.safe.digest(h.RUN/'analysis_inputs.json'),
        'analysis_protocol.md':h.safe.digest(h.RUN/'analysis_protocol.md')})
    print(json.dumps({'status':'ANALYSIS_CONTRACT_FROZEN_BEFORE_DISPATCH','target_shots':1536,
        'data_union':3072,'floor':64,'bootstrap':10000,'new_qpu_seconds':0}),flush=True)
if __name__=='__main__':run()
