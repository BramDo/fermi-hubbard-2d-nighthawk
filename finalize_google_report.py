"""Independent SQLite aggregation and canonical report provenance."""
import json, math, sqlite3
from pathlib import Path
from convert_google_hubbard import RUN, save, digest
from package_google_conversion import audit_and_compare, artifact

SQL='''SELECT case_name, method, count(*) AS sites,
 sum(charge) AS N, avg(doublon) AS mean_D,
 sqrt(avg(spin*spin)) AS spin_RMS,
 avg(ref_doublon) AS ref_D, sqrt(avg(ref_spin*ref_spin)) AS ref_spin_RMS,
 sqrt(avg((charge-ref_charge)*(charge-ref_charge))) AS rms_charge,
 sqrt(avg((spin-ref_spin)*(spin-ref_spin))) AS rms_spin,
 sqrt(avg((doublon-ref_doublon)*(doublon-ref_doublon))) AS rms_D
 FROM local_profiles GROUP BY case_name, method ORDER BY case_name, method'''

def main():
    result=audit_and_compare()
    dbpath=RUN/'report_metrics.sqlite'
    if dbpath.exists(): raise FileExistsError(dbpath)
    db=sqlite3.connect(dbpath); db.create_function('sqrt',1,math.sqrt)
    db.execute('CREATE TABLE local_profiles (case_name TEXT, method TEXT, site_index INTEGER, charge REAL, spin REAL, doublon REAL, ref_charge REAL, ref_spin REAL, ref_doublon REAL, PRIMARY KEY(case_name,method,site_index))')
    for r in result['rows']:
        db.executemany('INSERT INTO local_profiles VALUES (?,?,?,?,?,?,?,?,?)',
            [(r['case'],r['group'],i,*p,*ref) for i,(p,ref) in enumerate(zip(r['profile'],r['reference_profile']))])
    db.commit(); db.row_factory=sqlite3.Row
    out=[dict(r) for r in db.execute(SQL)]; db.close()
    delta=0.
    for r in result['rows']:
        checked=next(x for x in out if x['case_name']==r['case'] and x['method']==r['group'])
        for k in ('N','mean_D','spin_RMS','ref_D','ref_spin_RMS','rms_charge','rms_spin','rms_D'):
            delta=max(delta,abs(checked[k]-r[k]))
            assert abs(checked[k]-r[k])<1e-12
            r[k]=checked[k]
    report=artifact(result)
    source=report['manifest']['sources'][0]
    source['query']['language']='sql'; source['query']['engine']='SQLite'
    source['query']['sql']=SQL
    source['query']['tables_used'].insert(0,'report_metrics.sqlite.local_profiles')
    source['query']['description']='Local Z/ZZ-to-occupancy conversion from convert_google_hubbard.py, followed by independent SQLite aggregation of all site profiles and their matched-within-model references; not merely reselecting precomputed metrics.'
    for item in report['manifest']['charts']+report['manifest']['tables']: item['source']=source
    with (RUN/'artifact.json').open('w',encoding='utf-8') as f: json.dump(report,f,indent=2,allow_nan=False)
    with (RUN/'report_metrics.sql').open('x',encoding='utf-8') as f: f.write(SQL+';\n')
    save(RUN/'report_sql_verification.json',dict(status='PASS',rows=len(out),max_abs_difference=delta,sqlite_sha256=digest(dbpath),sql=SQL))
    with (RUN/'source_snapshot/finalize_google_report.py').open('xb') as f: f.write(Path(__file__).read_bytes())
    print(json.dumps(dict(status='REPORT_READY',rows=len(out),independent_SQL_delta=delta)))

if __name__=='__main__': main()
