"""Freeze completed diagnostic evidence; zero provider calls."""
from pathlib import Path
import shutil
from run_hardware_control_5x5_once import ROOT,RUN,LOCK,read,save,digest,verify,require


def main():
    verify(RUN,'frozen_inputs_sha256.json'); verify(RUN,'preflight_sha256.json')
    verify(RUN/'analysis','sha256.json')
    receipt=read(RUN/'job_receipt.json')
    retrieved=read(RUN/'retrieval_verification.json')
    numbers=read(RUN/'native_number_verification.json')
    summary=read(RUN/'analysis/summary.json')
    require({receipt['job_id'],retrieved['job_id'],numbers['job_id'],summary['job_id']}=={'daer9j5nj4cs73afhofg'},'Wrong job')
    require(retrieved['actual_shots']==6144 and len(numbers['checks'])==12,'Incomplete delivery')
    require(read(RUN/'provider_cap_verification.json')['verified'],'Unverified provider cap')
    require(summary['usage']['qpu_charge_time_seconds']==3,'Unexpected charged usage')
    for check in numbers['checks']:
        require(check['N_operator_residual_and_pruning']<1e-7,'Number-operator verification failed')
        path=RUN/'provider_inputs'/f"circuit_{check['index']:03d}.qpy"
        require(digest(path)==check['source_qpy_sha256'],'Verified circuit changed')
    require(digest(ROOT/'audit_hardware_control_5x5_number.py')==numbers['source_sha256'],'Audit source changed')
    extra=RUN/'additional_checks'; extra.mkdir()
    for name in ('audit_hardware_control_5x5_number.py',Path(__file__).name):
        shutil.copyfile(ROOT/name,extra/name)
    shutil.copyfile(RUN/'LOG.md',RUN/'LOG_at_delivery.md')
    shutil.copyfile(LOCK,RUN/'submission_attempt_snapshot.json')
    save(RUN/'COMPLETION.json',{'status':'COMPLETE_PREPARATION_PASS_DYNAMICS_FAIL',
        'job_id':receipt['job_id'],'QPU_seconds_charged':3,'cap_seconds':5,
        'submitted_jobs':1,'shots':6144,'circuits':12,'new_tests':8,'existing_regression_tests':29,
        'native_number_checks':12,'dense_operator_checks':6,'additional_hardware_authorized':False,
        'canonical_attempt_sha256':digest(LOCK),'mutable_hash_exclusions':['LOG.md'],
        'U0_reference_exact_for_finite_circuit':True,'preparation_small_bias_remains':True})
    save(RUN/'delivery_sha256.json',{str(p.relative_to(RUN)):digest(p)
        for p in RUN.rglob('*') if p.is_file() and p.name!='LOG.md'})
    verify(RUN,'delivery_sha256.json')
    print(read(RUN/'COMPLETION.json'))


if __name__=='__main__': main()
