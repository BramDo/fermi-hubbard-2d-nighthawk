"""Publish only the approved list update; preserve existing entries and site menu."""
import argparse, base64, datetime as dt, difflib, hashlib, json, re, shlex, subprocess
from pathlib import Path
import requests
from edukaizen_series3_release import ROOT, SITE, save, ssh, wp

LIST=ROOT.parent/'pro-student-quantum-advantage-list'
OUT=ROOT/'publication/advantage_list/2026-09-07_v1'
ENTRY='fermi-hubbard-2d-nighthawk-72q'
def digest(text): return hashlib.sha256(text.encode()).hexdigest()
def prepare():
    if OUT.exists(): raise FileExistsError('Preserve existing audit.')
    OUT.mkdir(parents=True)
    current=wp(['post','get','451','--field=post_content'])
    # WP-CLI appends a newline; JSON retrieval below is authoritative for hashing.
    post=json.loads(wp(['post','get','451','--format=json']))
    current=post['post_content']; (OUT/'before.html').write_text(current,encoding='utf-8')
    old=subprocess.check_output(['git','show','HEAD:docs/edukaizen-page.html'],cwd=LIST,text=True)
    if current.rstrip()!=old.rstrip():
        print(''.join(list(difflib.unified_diff(old.splitlines(True),current.splitlines(True)))[:80]))
        raise RuntimeError('Live list differs from the known baseline; merge rather than overwrite.')
    new=(LIST/'docs/edukaizen-page.html').read_text(encoding='utf-8')
    prior=dict(re.findall(r'(<section class="psqal-entry" id="([^"]+)">.*?</section>)',old,re.S))
    assert len(prior)==6 and all(section in new for section in prior)
    assert new.count('id="'+ENTRY+'"')==1
    entry=json.loads((LIST/'entries'/f'{ENTRY}.json').read_text())
    classical=json.loads((ROOT/'results_cuprate_2d/classical_full_6x6_mps_T04_chi64_v1/summary.json').read_text())
    provider=json.loads((ROOT/'results_cuprate_2d/hardware_compact_tflo_2026-09-07_v1/provider_metrics.json').read_text())
    assert entry['classical_baselines'][0]['seconds']==classical['result']['kernel_seconds']
    assert entry['classical_baselines'][1]['seconds']==classical['process_timing']['cold_worker_seconds']
    assert entry['quantum']['timings'][0]['seconds']==provider['usage']['qpu_charge_time_seconds']
    delta=(dt.datetime.fromisoformat(provider['timestamps']['finished'])-dt.datetime.fromisoformat(provider['timestamps']['running'])).total_seconds()
    assert entry['quantum']['timings'][2]['seconds']==delta
    assert abs(entry['comparison']['ratio']-classical['result']['kernel_seconds']/7)<1e-12
    assert classical['certified_6x6_error_bound'] is False and classical['chi128_performed'] is False
    try:
        import jsonschema
    except ImportError: raise RuntimeError('JSON schema validation unavailable; do not skip it.')
    schema=json.loads((LIST/'schema/entry.schema.json').read_text())
    for path in (LIST/'entries').glob('*.json'): jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker()).validate(json.loads(path.read_text()))
    payload=dict(page_id=451,before_sha256=digest(current),after_sha256=digest(new),html=new)
    save(OUT/'payload.json',payload)
    save(OUT/'preflight.json',dict(status='READY',old_entries_preserved=6,schema_valid_entries=7,source_timing_checks=True,list_baseline_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=LIST,text=True).strip(),page_id=451))
    print(json.dumps(dict(status='READY',old_entries_preserved=6,schema_valid_entries=7,source_timing_checks=True)))
def publish():
    payload=json.loads((OUT/'payload.json').read_text())
    if (OUT/'transport.json').exists(): raise RuntimeError('Inspect the existing publication attempt before retrying.')
    remote='/var/www/vhosts/edukaizen.nl/private/advantage-list-'+dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    save(OUT/'transport.json',dict(remote_directory=remote,status='STARTED'))
    ssh('umask 077; mkdir -m 700 -- '+shlex.quote(remote))
    for local,name in [(OUT/'payload.json','payload.json'),(ROOT/'scripts/publish_advantage_list.php','publish.php')]: subprocess.run(['scp','-q','-o','BatchMode=yes',str(local),'strato:'+remote+'/'+name],check=True)
    print(ssh('/opt/plesk/php/8.3/bin/php -l '+shlex.quote(remote+'/publish.php')).strip(),flush=True)
    save(OUT/'backup_receipt.json',dict(path=remote+'/backup.sql',result=wp(['db','export',remote+'/backup.sql','--add-drop-table']).strip(),downloaded=False))
    receipt=json.loads(wp(['eval-file',remote+'/publish.php'])); save(OUT/'publish_receipt.json',receipt)
    save(OUT/'cache_receipt.json',dict(result=wp(['cache','flush']).strip()))
    print(json.dumps(receipt))
def verify():
    url=SITE+'/pro-student-quantum-advantage-list/'
    response=requests.get(url,params={'nh_list_verify':'20260907-v1'},timeout=35,headers={'Cache-Control':'no-cache'})
    assert response.status_code==200
    page=response.text
    assert page.count('id="'+ENTRY+'"')==1 and '#'+ENTRY in page
    section=re.search(r'<section class="psqal-entry" id="'+ENTRY+r'">(.*?)</section>',page,re.S).group(1)
    for token in ['21.55x','circa 20x','Local execution-metric ratio','accuracy unvalidated','Both TFLO holdout checks failed','private GitHub repository','150.81918','7 s',SITE+'/2d-local-quantum-advantage/']:
        assert token in section,token
    assert '7 student-scale project reports' in page and 'Five complete' not in page
    assert 'menu-item-1119' in page and 'Hubbard' in page
    save(OUT/'public_verification.json',dict(status='PUBLIC_HTTP_VERIFIED',url=url+'#'+ENTRY,status_code=200,entry_count=7,claim_and_access_boundaries_visible=True,hubbard_menu_retained=True,visual_browser_check=False))
    print(json.dumps(dict(status='PUBLIC_HTTP_VERIFIED',url=url+'#'+ENTRY)))
def verify_github():
    repo='BramDo/pro-student-quantum-advantage-list'
    def gh(path): return json.loads(subprocess.check_output(['gh','api',path],text=True))
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=LIST,text=True).strip()
    commit=gh('repos/'+repo+'/commits/main'); assert commit['sha']==sha
    metadata=gh('repos/'+repo+'/contents/entries/'+ENTRY+'.json?ref='+sha)
    expected=json.loads((LIST/'entries'/f'{ENTRY}.json').read_text())
    assert json.loads(base64.b64decode(metadata['content']))==expected
    checks=gh('repos/'+repo+'/actions/runs?head_sha='+sha)['workflow_runs']
    states={r['name']:dict(status=r['status'],conclusion=r['conclusion'],url=r['html_url']) for r in checks}
    if any(states.get(name,{}).get('conclusion')!='success' for name in ['Validate list','pages build and deployment']):
        print(json.dumps(dict(status='DEPLOYMENT_PENDING',workflows=states))); return
    pages='https://bramdo.github.io/pro-student-quantum-advantage-list/'
    site=requests.get(pages,params={'v':sha},timeout=35)
    feed=requests.get(pages+'data/advantage-list.json',params={'v':sha},timeout=35)
    assert site.status_code==200 and feed.status_code==200
    assert 'id="'+ENTRY+'"' in site.text and '21.55x' in site.text and 'private GitHub repository' in site.text
    data=feed.json(); assert data['entry_count']==7
    assert next(e for e in data['entries'] if e['id']==ENTRY)==expected
    private=gh('repos/BramDo/fermi-hubbard-2d-nighthawk'); assert private['private'] is True
    save(OUT/'github_verification.json',dict(status='GITHUB_AND_PAGES_VERIFIED',commit=sha,entry_url=metadata['html_url'],pages_url=pages+'#'+ENTRY,feed_url=pages+'data/advantage-list.json',entry_count=7,source_entry_matches=True,workflows=states,research_repository_private=True))
    save(OUT/'public_entry_snapshot.json',expected)
    print(json.dumps(dict(status='GITHUB_AND_PAGES_VERIFIED',commit=sha,entry_count=7,research_repository_private=True)))
if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('action',choices=['prepare','publish','verify','verify-github']); args=parser.parse_args()
    {'prepare':prepare,'publish':publish,'verify':verify,'verify-github':verify_github}[args.action]()
