"""Build/publish only the approved public articles, never the private run archive."""
import argparse, concurrent.futures, datetime as dt, hashlib, html, json, re, shlex, subprocess
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'publication/edukaizen_series3'
OUT=BASE/'releases/2026-09-07_v1'
SITE='https://edukaizen.nl'
HUB='2d-local-quantum-advantage'
WP='/opt/plesk/php/8.3/bin/php /usr/local/bin/wp --allow-root'
WEBROOT='/var/www/vhosts/edukaizen.nl/httpdocs'
SLUGS=[HUB,'1-laptop-versus-quantumcomputer','2-fermionmodel','3-mapping-circuitdiepte','4-pilots-shots-ruis','5-foutmitigatie','6-resultaten','7-snelheidswinst','8-google-bonsai','9-volgende-stap']
LABELS=['2D Local Quantum Advantage','Deel 1: Doel en budget','Deel 2: Fermionmodel','Deel 3: Mapping en diepte','Deel 4: Pilots en shots','Deel 5: Foutmitigatie','Deel 6: 6x6-resultaten','Deel 7: Circa 20x','Deel 8: Google en Bonsai','Deel 9: Volgende stap']

def save(path,value):
    with path.open('x',encoding='utf-8') as f: json.dump(value,f,indent=2,ensure_ascii=False)

def ssh(command):
    return subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','strato',command],text=True)

def wp(args): return ssh('cd '+shlex.quote(WEBROOT)+' && '+WP+' '+shlex.join(args))

def build():
    if OUT.exists(): raise FileExistsError('Preserve an existing release; inspect it before making another.')
    OUT.mkdir(parents=True)
    draft=json.loads((BASE/'manifest.json').read_text())
    assert draft['status']=='DRAFT_NOT_PUBLISHED' and len(draft['pages'])==10
    urls=[SITE+'/'+HUB+'/']+[SITE+'/'+HUB+'/'+s+'/' for s in SLUGS[1:]]
    pages=[]
    for p in draft['pages']:
        i=p['part']; source=ROOT/p['wordpress_html']; raw=source.read_text(encoding='utf-8')
        body=re.sub(r'^<nav\b.*?</nav>\s*','',raw,count=1,flags=re.S)
        marker='<p><strong>CONCEPT — nog niet gepubliceerd.</strong></p>'
        assert body.count(marker)==1
        body=body.replace(marker,'').lstrip()
        if i==0:
            newindex='<h2>Leesvolgorde</h2>\n<ol>\n'+''.join('<li><a href="'+urls[q['part']]+'">Deel '+str(q['part'])+': '+html.escape(q['title'])+'</a></li>\n' for q in draft['pages'][1:])+'</ol>'
            body,n=re.subn(r'<h2>Leesvolgorde</h2>\s*<ol>.*?</ol>',lambda m:newindex,body,count=1,flags=re.S); assert n==1
            body,n=re.subn(r'<p>De repository is voorlopig privé\..*?</p>','<p>De negen artikelen zijn hieronder toegankelijk. De bijbehorende GitHub-repository blijft privé; toegang tot het onderzoeksarchief vereist toestemming. De eerdere Hubbard-series blijven beschikbaar.</p>',body,count=1,flags=re.S); assert n==1
            body='<p><strong>Hubbard serie 3 — IBM Nighthawk, 72 fermionmodi en onze lokale snelheidsbenchmark.</strong></p>\n'+body
        nav=['<a href="'+urls[0]+'">2D Local Quantum Advantage</a>']
        for j,label in [(i-1,'Vorige'),(i+1,'Volgende')]:
            if 0<=j<10: nav.append('<a href="'+urls[j]+'">'+label+'</a>')
        content='<section class="nighthawk-series3" id="nighthawk-part-'+str(i)+'">\n<nav class="fh-series-nav" aria-label="Artikelnavigatie">'+' | '.join(nav)+'</nav>\n'+body+'</section>\n'
        assert 'CONCEPT' not in content and 'hubbard-nighthawk-serie-3/' not in content
        assert content.count('[latex syntax="display"]')==content.count('[/latex]')
        assert '/mnt/c/' not in content and 'C:\\Users' not in content
        title=LABELS[0] if i==0 else 'Deel '+str(i)+': '+p['title']
        pages.append(dict(part=i,title=title,slug=SLUGS[i],url=urls[i],menu_label=LABELS[i],html=content,
            excerpt='Hubbard-serie 3: 2D-dynamica op Nighthawk en de circa 20x-verhouding tussen geregistreerde QPU-tijd en lokale klassieke rekenkerntijd. Nauwkeurigheid en totale doorlooptijd blijven afzonderlijke vragen.',
            source=p['source'],source_sha256=hashlib.sha256((ROOT/p['source']).read_bytes()).hexdigest(),sha256=hashlib.sha256(content.encode()).hexdigest()))
        (OUT/f'{i:02d}.html').write_text(content,encoding='utf-8')
    package=dict(site=SITE,release='series3-2026-09-07-v1',title=LABELS[0],hub_slug=HUB,pages=pages,public_content_only=True,source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    save(OUT/'publish_package.json',package)
    print(json.dumps({'status':'PUBLICATION_PACKAGE_READY','pages':10,'hub_url':urls[0],'public_html_bytes':sum(len(p['html'].encode()) for p in pages)}))

def inventory():
    posts=json.loads(wp(['post','list','--post_type=page,post','--post_status=publish,draft,private,pending,future,trash','--posts_per_page=-1','--fields=ID,post_title,post_name,post_parent,post_status','--format=json']))
    menu=json.loads(wp(['menu','item','list','3','--fields=db_id,title,menu_item_parent,position,url','--format=json']))
    relevant=[p for p in posts if p['post_name'] in SLUGS or 'hubbard-nighthawk' in p['post_name'] or p['post_name'] in ['fermi-hubbard-2d-cuprate-series','fermi-hubbard-quantum-simulation-project']]
    result=dict(site=wp(['option','get','home']).strip(),post_count=len(posts),relevant_pages=relevant,menu_items=menu)
    save(OUT/'inventory_before.json',result)
    print(json.dumps({'status':'INVENTORIED','relevant_pages':relevant,'existing_menu_count':len(menu)}))

def publish():
    package=json.loads((OUT/'publish_package.json').read_text())
    if (OUT/'transport.json').exists(): raise RuntimeError('A transport attempt exists: inspect/recover its receipt before retrying.')
    inventory()
    # Keep the database backup outside the document root, with a private directory.
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    remote='/var/www/vhosts/edukaizen.nl/private/series3-publish-'+stamp
    save(OUT/'transport.json',dict(remote_directory=remote,status='STARTED',contains_database_backup_on_server_only=True))
    private='/var/www/vhosts/edukaizen.nl/private'
    ssh('umask 077; if [ ! -e '+shlex.quote(private)+' ]; then mkdir -m 700 -- '+shlex.quote(private)+'; fi; test -d '+shlex.quote(private)+' && mkdir -m 700 -- '+shlex.quote(remote))
    for src,name in [(OUT/'publish_package.json','publish_package.json'),(ROOT/'scripts/publish_edukaizen_series3.php','publish.php')]:
        subprocess.run(['scp','-q','-o','BatchMode=yes',str(src),'strato:'+remote+'/'+name],check=True)
    print(ssh('/opt/plesk/php/8.3/bin/php -l '+shlex.quote(remote+'/publish.php')).strip(),flush=True)
    backup=wp(['db','export',remote+'/backup.sql','--add-drop-table'])
    save(OUT/'backup_receipt.json',dict(remote_path=remote+'/backup.sql',result=backup.strip(),downloaded=False))
    print('Private server backup completed; publishing the ten scoped pages.',flush=True)
    try:
        raw=wp(['eval-file',remote+'/publish.php'])
    except subprocess.CalledProcessError:
        # Receipt recovery is read-only and prevents blind duplicate submissions.
        recovered=ssh('test ! -f '+shlex.quote(remote+'/publish_receipt.json')+' || cat '+shlex.quote(remote+'/publish_receipt.json'))
        if recovered.strip(): save(OUT/'partial_receipt.json',json.loads(recovered))
        raise
    receipt=json.loads(raw); save(OUT/'publish_receipt.json',receipt)
    assert receipt['status']=='PUBLISHED_AND_SERVER_VERIFIED'
    cache=wp(['cache','flush']); save(OUT/'cache_receipt.json',dict(result=cache.strip()))
    print(json.dumps({'status':receipt['status'],'hub':receipt['pages'][0],'pages':len(receipt['pages']),'unrelated_posts_preserved':receipt['unrelated_posts_preserved'],'existing_menu_items_preserved':receipt['existing_menu_items_preserved']},ensure_ascii=False))

def verify():
    receipt=json.loads((OUT/'publish_receipt.json').read_text()); package=json.loads((OUT/'publish_package.json').read_text())
    expected=package['pages']
    def check(page):
        r=requests.get(page['url'],params={'nh_verify':package['release']},timeout=35,headers={'Cache-Control':'no-cache'})
        markup=r.text
        checks=dict(status_code=r.status_code,has_series_content='nighthawk-part-'+str(page['part']) in markup,
            has_title=html.escape(page['title']) in markup or page['title'] in html.unescape(markup),
            has_nav='fh-series-nav' in markup,no_draft_marker='CONCEPT — nog niet gepubliceerd' not in markup,
            no_old_hub_link=SITE+'/hubbard-nighthawk-serie-3/' not in markup,
            no_raw_latex_shortcode='[latex' not in markup,mathjax_script=('MathJax' in markup or 'mathjax' in markup))
        if page['part']==0: checks['all_article_links']=all(p['url'] in markup for p in expected[1:])
        (OUT/f'live_{page["part"]:02d}.html').write_text(markup,encoding='utf-8')
        assert checks['status_code']==200 and all(v for k,v in checks.items() if k not in ('status_code','mathjax_script')),checks
        if '[latex' in page['html']: assert checks['mathjax_script']
        return dict(part=page['part'],url=page['url'],checks=checks)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool: pages=list(pool.map(check,expected))
    home=requests.get(SITE+'/',params={'nh_verify':package['release']},timeout=35).text
    assert expected[0]['url'] in home and LABELS[0] in home
    menus=json.loads(wp(['menu','item','list','3','--fields=db_id,title,menu_item_parent,position,url','--format=json']))
    before=json.loads((OUT/'inventory_before.json').read_text())['menu_items']; byid={m['db_id']:m for m in menus}
    assert all({k:v for k,v in byid[m['db_id']].items() if k!='position'}=={k:v for k,v in m.items() if k!='position'} for m in before)
    old_ids=[m['db_id'] for m in before]
    assert [m['db_id'] for m in menus if m['db_id'] in old_ids]==old_ids
    result=dict(status='PUBLIC_HTTP_VERIFIED',pages=pages,homepage_link=True,existing_menu_fields_and_relative_order_unchanged=True,computed_menu_position_changes=receipt.get('computed_menu_position_changes',[]),publication=receipt['release'])
    save(OUT/'public_verification.json',result)
    print(json.dumps({'status':result['status'],'http200_pages':len(pages),'homepage_link':True,'existing_menu_items_preserved':len(before)}))

def audit():
    """Read-only recovery inventory; never blindly resubmit a completed stage."""
    before=json.loads((OUT/'inventory_before.json').read_text())['menu_items']
    current=json.loads(wp(['menu','item','list','3','--fields=db_id,title,menu_item_parent,position,url','--format=json']))
    byid={m['db_id']:m for m in current}
    changes=[dict(before=m,after=byid.get(m['db_id'])) for m in before if byid.get(m['db_id'])!=m]
    partial=json.loads((OUT/'partial_receipt.json').read_text())
    print(json.dumps(dict(changed_old_menu_items=changes,receipt=partial),ensure_ascii=False,indent=2))
    print(wp(['post','list','--post_type=nav_menu_item','--posts_per_page=-1','--fields=ID,post_title,menu_order','--format=json']))

def recover():
    if (OUT/'publish_receipt.json').exists(): raise FileExistsError('Final receipt already exists.')
    remote=json.loads((OUT/'transport.json').read_text())['remote_directory']
    assert remote=='/var/www/vhosts/edukaizen.nl/private/series3-publish-20260907T142126Z'
    subprocess.run(['scp','-q','-o','BatchMode=yes',str(ROOT/'scripts/verify_edukaizen_series3.php'),'strato:'+remote+'/verify.php'],check=True)
    print(ssh('/opt/plesk/php/8.3/bin/php -l '+shlex.quote(remote+'/verify.php')).strip(),flush=True)
    receipt=json.loads(wp(['eval-file',remote+'/verify.php']))
    assert receipt['status']=='PUBLISHED_AND_SERVER_VERIFIED'
    save(OUT/'publish_receipt.json',receipt)
    save(OUT/'cache_receipt.json',dict(result=wp(['cache','flush']).strip()))
    print(json.dumps(dict(status=receipt['status'],pages=len(receipt['pages']),unrelated_posts_preserved=receipt['unrelated_posts_preserved'],existing_menu_items_preserved=receipt['existing_menu_items_preserved'],computed_menu_position_changes=receipt['computed_menu_position_changes'])))

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('action',choices=['build','publish','verify','audit','recover']); a=ap.parse_args()
    {'build':build,'publish':publish,'verify':verify,'audit':audit,'recover':recover}[a.action]()
