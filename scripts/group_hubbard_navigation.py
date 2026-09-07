"""One approved Hubbard menu grouping, with guarded receipt and public DOM checks."""
import datetime as dt, json, shlex, subprocess, sys
from html.parser import HTMLParser
import requests
from edukaizen_series3_release import BASE, ROOT, SITE, save, ssh, wp

OUT=BASE/'navigation/2026-09-07_hubbard_group'

class MenuParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.depth=0; self.stack=[]; self.nodes={}; self.anchor=None
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='ul':
            if self.depth or a.get('id')=='primary-menu': self.depth+=1
        if not self.depth: return
        if tag=='li':
            mid=int(a['id'].removeprefix('menu-item-'))
            self.nodes[mid]=dict(parent=self.stack[-1] if self.stack else 0,title='',url='')
            self.stack.append(mid)
        if tag=='a' and self.stack:
            self.anchor=self.stack[-1]; self.nodes[self.anchor]['url']=a.get('href','')
    def handle_endtag(self,tag):
        if not self.depth: return
        if tag=='a': self.anchor=None
        if tag=='li': self.stack.pop()
        if tag=='ul': self.depth-=1
    def handle_data(self,data):
        if self.anchor is not None: self.nodes[self.anchor]['title']+=data

def verify(receipt):
    # Compare displayed labels with pre-change public HTML, not raw WP strings:
    # the site's typography filter renders e.g. "3x3" as "3×3".
    label_path=OUT/'rendered_labels_baseline.json'
    if label_path.exists(): rendered_labels=json.loads(label_path.read_text())
    else:
        prior=MenuParser(); prior.feed((BASE/'releases/2026-09-07_v1/live_00.html').read_text(encoding='utf-8'))
        assert len(prior.nodes)==98 and receipt['group_id'] not in prior.nodes
        rendered_labels={str(mid):node['title'] for mid,node in prior.nodes.items()}
        save(label_path,rendered_labels)
    pages=[]
    for url in [SITE+'/']+[b['url'] for b in receipt['branches']]:
        r=requests.get(url,params={'nh_menu_verify':'20260907-grouped'},headers={'Cache-Control':'no-cache'},timeout=35)
        assert r.status_code==200
        parsed=MenuParser(); parsed.feed(r.text); nodes=parsed.nodes; gid=receipt['group_id']
        assert nodes[gid]==dict(parent=0,title='Hubbard',url='#')
        assert [mid for mid,m in nodes.items() if m['parent']==gid]==[332,373,1109]
        for sid,old in receipt['menu_before'].items():
            mid=int(sid); parent=gid if mid in [332,373,1109] else old['parent']
            assert nodes[mid]==dict(parent=parent,title=rendered_labels[sid],url=old['url']), (url,mid,nodes[mid],old)
        for root,count in [(332,10),(373,6),(1109,9)]:
            assert sum(m['parent']==root for m in nodes.values())==count
        assert [m['title'] for m in nodes.values() if m['parent']==0][:2]==['News','Hubbard']
        pages.append(dict(url=url,status_code=200,hubbard_is_single_top_level=True,series_order=[332,373,1109],all_existing_links_preserved=True))
    result=dict(status='PUBLIC_MENU_DOM_VERIFIED',group_id=receipt['group_id'],pages=pages,visual_browser_check=False,visual_check_note='Chrome binding unavailable; server fields and public HTML hierarchy verified.')
    save(OUT/'public_verification.json',result)
    print(json.dumps(dict(status=result['status'],group_id=receipt['group_id'],verified_pages=len(pages),three_series_under_one_button=True)))

if __name__=='__main__':
    if sys.argv[1:]==['--verify-only']:
        receipt=json.loads((OUT/'navigation_receipt.json').read_text())
        assert receipt['status']=='GROUPED_AND_SERVER_VERIFIED'
        verify(receipt); sys.exit(0)
    resume=sys.argv[1:]==['--resume-preflight']
    if OUT.exists():
        if not resume: raise FileExistsError('Inspect the existing attempt before retrying.')
        remote=json.loads((OUT/'transport.json').read_text())['remote_directory']
        assert remote=='/var/www/vhosts/edukaizen.nl/private/hubbard-navigation-20260907T142958Z'
        assert not (OUT/'navigation_receipt.json').exists() and not (OUT/'partial_receipt.json').exists()
        ssh('test ! -e '+shlex.quote(remote+'/navigation_receipt.json')+' && test ! -e '+shlex.quote(remote+'/navigation_before.json'))
        current=json.loads(wp(['menu','item','list','3','--fields=db_id,title,menu_item_parent,object_id,type,url','--format=json']))
        assert len(current)==98 and not any(m['title']=='Hubbard' for m in current)
        scoped={m['db_id']:m for m in current if m['db_id'] in [332,373,1109]}
        assert len(scoped)==3 and all(str(m['menu_item_parent'])=='0' for m in scoped.values())
        assert scoped[373]['type']=='custom' and int(scoped[373]['object_id'])==373
        save(OUT/'preflight_recovery.json',dict(reason='Initial preflight expected a page-linked Hubbard 2D item; actual item 373 is custom. Abort occurred before any menu write.',checked_no_new_hub_or_parent_changes=True,existing_private_backup=json.loads((OUT/'backup_receipt.json').read_text()),current_series=scoped))
    else:
        if resume: raise RuntimeError('No existing preflight to resume.')
        OUT.mkdir(parents=True)
        remote='/var/www/vhosts/edukaizen.nl/private/hubbard-navigation-'+dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        save(OUT/'transport.json',dict(remote_directory=remote,status='STARTED'))
        ssh('umask 077; mkdir -m 700 -- '+shlex.quote(remote))
        save(OUT/'backup_receipt.json',dict(path=remote+'/backup.sql',result=wp(['db','export',remote+'/backup.sql','--add-drop-table']).strip(),downloaded=False))
    subprocess.run(['scp','-q','-o','BatchMode=yes',str(ROOT/'scripts/group_hubbard_menu.php'),'strato:'+remote+'/group.php'],check=True)
    print(ssh('/opt/plesk/php/8.3/bin/php -l '+shlex.quote(remote+'/group.php')).strip(),flush=True)
    print('Private backup completed; grouping existing menu branches.',flush=True)
    try: receipt=json.loads(wp(['eval-file',remote+'/group.php']))
    except subprocess.CalledProcessError:
        partial=ssh('test ! -f '+shlex.quote(remote+'/navigation_receipt.json')+' || cat '+shlex.quote(remote+'/navigation_receipt.json'))
        if partial.strip(): save(OUT/'partial_receipt.json',json.loads(partial))
        raise
    save(OUT/'navigation_receipt.json',receipt)
    print(json.dumps(dict(status=receipt['status'],group_id=receipt['group_id'],pages_preserved=receipt['pages_preserved'],existing_menu_items_preserved=receipt['existing_menu_items_preserved'])),flush=True)
    save(OUT/'cache_receipt.json',dict(result=wp(['cache','flush']).strip()))
    verify(receipt)
