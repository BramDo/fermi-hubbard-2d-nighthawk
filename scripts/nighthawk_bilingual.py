"""Guarded NL/EN publication; source articles, formulas and menu are preserved."""
import argparse, collections, concurrent.futures, datetime as dt, hashlib, html, json, re, shlex, subprocess
from html.parser import HTMLParser
from edukaizen_series3_release import ROOT, BASE, SITE, save, ssh, wp
import requests

OUT=BASE/'bilingual/2026-09-07_v1'
EN_SLUGS=['2d-local-quantum-advantage-en','1-laptop-versus-quantum-computer','2-fermion-model','3-mapping-circuit-depth','4-pilots-shots-noise','5-error-mitigation','6-results','7-speed-comparison','8-google-bonsai','9-next-step']
TITLES=['2D Local Quantum Advantage','A laptop as our benchmark: the Nighthawk project','What does U=8 dynamics mean? The full fermion model','From a 2D lattice to hardware: mapping and circuit depth','Small pilots: is the problem shots or the circuit?','Readout, ZNE, PEC and TFLO: what did we actually use?','Our 6x6 results: charge, spin and doublons','Approximately 20x: our local timing milestone explained','How close are we to Google and the Bonsai results?','From a fast run to a reliable answer']
EN_URLS=[SITE+'/'+EN_SLUGS[0]+'/']+[SITE+'/'+EN_SLUGS[0]+'/'+s+'/' for s in EN_SLUGS[1:]]
CSS='<style>.nighthawk-series3 .nh-language-switch{display:flex;flex-wrap:wrap;gap:.55rem;margin:0 0 1rem}.nighthawk-series3 .nh-language-switch a{display:inline-block;padding:.5rem .85rem;border:1px solid #17212b;border-radius:4px;background:#fff;color:#17212b;text-decoration:none;font-weight:600}.nighthawk-series3 .nh-language-switch a[aria-current="page"]{background:#17212b;color:#fff}.nighthawk-series3 .nh-language-switch a:focus-visible{outline:3px solid #087f73;outline-offset:3px}</style>'
def sha(s): return hashlib.sha256(s.encode()).hexdigest()
def body(s):
    s=re.sub(r'^<section[^>]*>\s*','',s,count=1)
    s=re.sub(r'^<nav\b.*?</nav>\s*','',s,count=1,flags=re.S)
    return re.sub(r'</section>\s*$','',s).strip()
def numbers(s,lang):
    s=html.unescape(re.sub(r'<[^>]+>',' ',s))
    tokens=re.findall(r'(?<![\w.])[-+]?\d+(?:[.,]\d+)*(?!\d|[.,]\d)',s)
    def canonical(t):
        t=t.replace('.','').replace(',','.') if lang=='nl' else t.replace(',','')
        return format(float(t),'.12g')
    return collections.Counter(map(canonical,tokens))
def switch(nl,en,lang):
    links=[]
    for code,label,url in [('nl','Nederlands',nl),('en','English',en)]:
        active=' aria-current="page"' if code==lang else ''
        links.append(f'<a href="{url}" hreflang="{code}" lang="{code}"{active}>{label}</a>')
    return CSS+'<nav class="nh-language-switch" aria-label="'+('Taalkeuze' if lang=='nl' else 'Language')+'">'+''.join(links)+'</nav>\n'
def inventory():
    if (OUT/'inventory.json').exists(): raise FileExistsError('Inventory already exists; inspect before retrying.')
    OUT.mkdir(parents=True,exist_ok=True)
    old=json.loads((BASE/'releases/2026-09-07_v1/publish_receipt.json').read_text())
    def get(row):
        p=json.loads(wp(['post','get',str(row['id']),'--format=json']))
        assert int(p['ID'])==row['id'] and p['post_status']=='publish' and not p['post_password']
        assert sha(p['post_content'])==row['sha256'],('Dutch article edited since source release',row['id'])
        return dict(part=row['part'],id=row['id'],title=p['post_title'],slug=p['post_name'],parent=int(p['post_parent']),url=row['url'],html=p['post_content'],sha256=sha(p['post_content']))
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool: nl=list(pool.map(get,old['pages']))
    pages=json.loads(wp(['post','list','--post_type=page','--post_status=any','--posts_per_page=-1','--fields=ID,post_name,post_parent,post_status','--format=json']))
    matches=[p for p in pages if p['post_name']==EN_SLUGS[0]]
    assert not matches,('English hub already exists; inspect ownership before updating',matches)
    menu=json.loads(wp(['menu','item','list','3','--fields=db_id,title,menu_item_parent,position,url','--format=json']))
    assert any(m['db_id']==1119 and m['title']=='Hubbard' for m in menu)
    plugins=json.loads(wp(['plugin','list','--status=active','--field=name','--format=json']))
    assert 'mathjax-latex' in plugins
    save(OUT/'inventory.json',dict(nl=nl,menu=menu,english_hub_matches=matches,mathjax_active=True))
    print(json.dumps(dict(status='INVENTORIED',nl_pages=len(nl),menu_items=len(menu),english_hub_exists=False)))
def build():
    if (OUT/'payload.json').exists(): raise FileExistsError('Preserve built release.')
    inv=json.loads((OUT/'inventory.json').read_text()); pairs=[]; checks=[]
    for p in inv['nl']:
        i=p['part']; source=body(p['html']); translated=(OUT/f'source/en/{i:02d}.html').read_text(encoding='utf-8').strip()
        formulas=re.findall(r'\[latex syntax="display"\].*?\[/latex\]',source,re.S)
        if '{{HAMILTONIAN}}' in translated: assert len(formulas)==1; translated=translated.replace('{{HAMILTONIAN}}',formulas[0])
        assert re.findall(r'\[latex syntax="display"\].*?\[/latex\]',translated,re.S)==formulas
        if i:
            assert numbers(source,'nl')==numbers(translated,'en'),(i,numbers(source,'nl')-numbers(translated,'en'),numbers(translated,'en')-numbers(source,'nl'))
            assert re.findall(r'href="([^"]+)"',source)==re.findall(r'href="([^"]+)"',translated),(i,'Source links differ')
            for tag in ['p','h2','table','tr','td','th']:
                assert len(re.findall('<'+tag+r'(?:>|\s)',source))==len(re.findall('<'+tag+r'(?:>|\s)',translated)),(i,tag,'Translation structure differs')
        else:
            index='<ol>'+''.join(f'<li><a href="{EN_URLS[j]}">Part {j}: {html.escape(TITLES[j])}</a></li>' for j in range(1,10))+'</ol>'
            translated=translated.replace('{{EN_INDEX}}',index)
        assert '{{' not in translated and 'CONCEPT' not in translated
        nav=[f'<a href="{EN_URLS[0]}">2D Local Quantum Advantage</a>']
        for j,label in [(i-1,'Previous'),(i+1,'Next')]:
            if 0<=j<10: nav.append(f'<a href="{EN_URLS[j]}">{label}</a>')
        en=f'<section class="nighthawk-series3" id="nighthawk-en-part-{i}" lang="en">\n'+switch(p['url'],EN_URLS[i],'en')+'<nav class="fh-series-nav" aria-label="Article navigation">'+' | '.join(nav)+'</nav>\n'+translated+'\n</section>\n'
        old_start=re.match(r'<section[^>]*>\s*',p['html']).group(0)
        new_start=old_start.replace('>',' lang="nl">',1)
        nl=p['html'].replace(old_start,new_start+switch(p['url'],EN_URLS[i],'nl'),1)
        assert nl.replace(new_start+switch(p['url'],EN_URLS[i],'nl'),old_start,1)==p['html']
        english=dict(part=i,title=TITLES[0] if not i else f'Part {i}: {TITLES[i]}',slug=EN_SLUGS[i],url=EN_URLS[i],html=en,sha256=sha(en))
        dutch=dict(p); dutch.update(html=nl,before_sha256=p['sha256'],sha256=sha(nl))
        pairs.append(dict(part=i,nl=dutch,en=english)); checks.append(dict(part=i,numbers_preserved=True if i else 'hub',formulas_preserved=len(formulas),dutch_body_unchanged=True))
        for lang,content in [('en',en),('nl',nl)]:
            folder=OUT/'rendered'/lang; folder.mkdir(parents=True,exist_ok=True); (folder/f'{i:02d}.html').write_text(content,encoding='utf-8')
    save(OUT/'payload.json',dict(release='nighthawk-bilingual-2026-09-07-v1',pairs=pairs))
    save(OUT/'translation_checks.json',dict(status='VALIDATED',pairs=checks))
    print(json.dumps(dict(status='BILINGUAL_PACKAGE_VALIDATED',pages=20,numerical_pairs=9)))
def publish():
    if (OUT/'transport.json').exists(): raise RuntimeError('Inspect the prior attempt; do not blindly republish.')
    remote='/var/www/vhosts/edukaizen.nl/private/nighthawk-bilingual-'+dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    save(OUT/'transport.json',dict(remote_directory=remote,status='STARTED'))
    ssh('umask 077; mkdir -m 700 -- '+shlex.quote(remote))
    for src,name in [(OUT/'payload.json','payload.json'),(ROOT/'scripts/publish_nighthawk_bilingual.php','publish.php')]: subprocess.run(['scp','-q','-o','BatchMode=yes',str(src),'strato:'+remote+'/'+name],check=True)
    print(ssh('/opt/plesk/php/8.3/bin/php -l '+shlex.quote(remote+'/publish.php')).strip(),flush=True)
    save(OUT/'backup_receipt.json',dict(path=remote+'/backup.sql',result=wp(['db','export',remote+'/backup.sql','--add-drop-table']).strip(),downloaded=False))
    print('Private backup complete; publishing language counterparts.',flush=True)
    try: result=json.loads(wp(['eval-file',remote+'/publish.php']))
    except subprocess.CalledProcessError:
        partial=ssh('test ! -f '+shlex.quote(remote+'/receipt.json')+' || cat '+shlex.quote(remote+'/receipt.json'))
        if partial.strip(): save(OUT/'partial_receipt.json',json.loads(partial))
        raise
    save(OUT/'publish_receipt.json',result); save(OUT/'cache_receipt.json',dict(result=wp(['cache','flush']).strip()))
    print(json.dumps(dict(status=result['status'],pairs=len(result['pairs']),en_hub=result['pairs'][0]['en']['url'],menu_unchanged=result['menu_unchanged'])))
class Inspect(HTMLParser):
    def __init__(self): super().__init__(); self.stack=[]; self.switches=[]; self.series=[]; self.current=None
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='nav': self.stack.append(a.get('class',''))
        if tag=='a' and self.stack and self.stack[-1]=='nh-language-switch': self.switches.append(a)
        if tag=='a' and self.stack and self.stack[-1]=='fh-series-nav': self.series.append(a.get('href'))
    def handle_endtag(self,tag):
        if tag=='nav' and self.stack: self.stack.pop()
def verify():
    payload=json.loads((OUT/'payload.json').read_text()); receipt=json.loads((OUT/'publish_receipt.json').read_text())
    def check(item):
        pair,lang=item; page=pair[lang]; r=requests.get(page['url'],params={'nh_lang_verify':payload['release']},timeout=35,headers={'Cache-Control':'no-cache'})
        assert r.status_code==200 and r.url.split('?')[0]==page['url']
        parsed=Inspect(); parsed.feed(r.text)
        assert len(parsed.switches)==2
        assert {a['hreflang']:a['href'] for a in parsed.switches}=={code:pair[code]['url'] for code in ['nl','en']}
        assert [a['hreflang'] for a in parsed.switches if a.get('aria-current')=='page']==[lang]
        expected=Inspect(); expected.feed(page['html']); assert parsed.series==expected.series
        marker='nighthawk-en-part-' if lang=='en' else 'nighthawk-part-'
        assert marker+str(pair['part']) in r.text and 'lang="'+lang+'"' in r.text
        assert '[latex' not in r.text and 'MathJax' in r.text
        if pair['part']==0: assert all(p[lang]['url'] in r.text for p in payload['pairs'][1:])
        return dict(part=pair['part'],language=lang,url=page['url'],http_status=200,reciprocal_switch=True,series_navigation=True,mathjax_markers=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: rows=list(pool.map(check,[(p,lang) for p in payload['pairs'] for lang in ['nl','en']]))
    before=json.loads((OUT/'inventory.json').read_text())['menu']; after=json.loads(wp(['menu','item','list','3','--fields=db_id,title,menu_item_parent,position,url','--format=json'])); assert before==after
    save(OUT/'public_verification.json',dict(status='PUBLIC_BILINGUAL_VERIFIED',pages=rows,menu_unchanged=True,visual_browser_check=False,visual_note='Public HTML and link targets checked; no browser screenshot claimed.'))
    print(json.dumps(dict(status='PUBLIC_BILINGUAL_VERIFIED',http200_pages=20,reciprocal_pairs=10,menu_unchanged=True)))
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('action',choices=['inventory','build','publish','verify']); a=ap.parse_args(); globals()[a.action]()
