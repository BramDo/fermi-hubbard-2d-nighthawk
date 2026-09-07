"""Bounded range reader for selected public Zenodo ZIP entries, no full ZIP."""
import argparse,hashlib,io,json,re,struct,time,zipfile
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parent
RUN=ROOT/'results_cuprate_2d/google_conversion_2026-09-07_v1'
BASE='https://zenodo.org/records/17881822/files/'
ZIP_URL=BASE+'programmable_simulation_fermi_hubbard.zip?download=1'
README_URL=BASE+'README.md?download=1'
MAX_TRANSFER=100_000_000

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,value):
    with p.open('x',encoding='utf-8') as f: json.dump(value,f,indent=2,allow_nan=False)
def log(event,**fields):
    row=dict(event=event,unix=time.time(),**fields)
    if RUN.exists():
        with (RUN/'fetch_log.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(row)+'\n')
    print(json.dumps(row),flush=True)

class BoundedHTTP:
    def __init__(self):
        self.session=requests.Session(); self.session.headers['User-Agent']='Hubbard-comparison/1.0 (public scientific data)'
        self.transferred=0; self.records=[]; self.total_size=None; self.etag=None
    def get(self,url,start=None,end=None,limit=200000):
        if self.transferred+limit>MAX_TRANSFER: raise ValueError('100MB per-action transfer limit')
        headers={} if start is None else {'Range':f'bytes={start}-{end}','Accept-Encoding':'identity'}
        with self.session.get(url,headers=headers,stream=True,timeout=(10,45)) as response:
            if response.status_code==429:
                log('rate_limited_stop',retry_after=response.headers.get('Retry-After')); raise RuntimeError('Rate limited; no automatic retry')
            expected=200 if start is None else 206
            if response.status_code!=expected: raise RuntimeError(f'Expected HTTP{expected}, got{response.status_code}; body not downloaded')
            if start is not None:
                match=re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)',response.headers.get('Content-Range',''))
                if not match or tuple(map(int,match.groups()[:2]))!=(start,end): raise ValueError('Range response mismatch')
                size=int(match[3])
                if self.total_size is not None and size!=self.total_size: raise ValueError('Remote ZIP size changed')
                self.total_size=size
                etag=response.headers.get('ETag')
                if self.etag is not None and etag is not None and etag!=self.etag: raise ValueError('Remote ETag changed')
                if etag: self.etag=etag
            chunks=[]; count=0
            for chunk in response.iter_content(65536):
                count+=len(chunk)
                if count>limit: raise ValueError('Response exceeds transfer bound')
                chunks.append(chunk)
            payload=b''.join(chunks)
            if start is not None and len(payload)!=end-start+1: raise ValueError('Truncated range')
            self.transferred+=count
            record=dict(url=url,start=start,end=end,bytes=count,status=response.status_code,
                content_range=response.headers.get('Content-Range'),etag=response.headers.get('ETag'),sha256=hashlib.sha256(payload).hexdigest())
            self.records.append(record); log('HTTP_read',start=start,end=end,bytes=count,total_transferred=self.transferred)
            return payload

class RangeZIP(io.RawIOBase):
    def __init__(self,http):
        self.http=http; http.get(ZIP_URL,0,0,limit=1); self.size=http.total_size; self.position=0; self.cache={}
    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.position
    def seek(self,offset,whence=0):
        value=offset if whence==0 else self.position+offset if whence==1 else self.size+offset
        if value<0 or value>self.size: raise ValueError('Seek out of ZIP')
        self.position=value; return value
    def read(self,n=-1):
        if n<0: n=self.size-self.position
        n=min(n,self.size-self.position)
        if n==0: return b''
        if n>40_000_000: raise ValueError('Single ZIP read exceeds40MB')
        start=self.position; end=start+n-1
        # Coalesce small metadata reads, but retrieve large compressed entries once.
        if n<=65536:
            a=(start//65536)*65536; b=min(self.size-1,max(end,a+65535)); key=(a,b)
            if key not in self.cache: self.cache[key]=self.http.get(ZIP_URL,a,b,limit=b-a+1)
            data=self.cache[key][start-a:start-a+n]
        else: data=self.http.get(ZIP_URL,start,end,limit=n)
        self.position+=len(data); return data

def index():
    if RUN.exists(): raise FileExistsError('Do not overwrite existing comparison; inspect/resume selected downloads')
    RUN.mkdir(); (RUN/'source_snapshot').mkdir(); (RUN/'downloads').mkdir()
    import shutil
    for name in ('GOOGLE_CONVERSION_PROTOCOL.md','fetch_google_hubbard_data.py'):
        shutil.copyfile(ROOT/name,RUN/'source_snapshot'/name)
    http=BoundedHTTP()
    readme=http.get(README_URL)
    with (RUN/'GOOGLE_DATA_README.md').open('xb') as f: f.write(readme)
    remote=RangeZIP(http)
    with zipfile.ZipFile(remote) as archive:
        entries=[dict(name=i.filename,bytes=i.file_size,compressed_bytes=i.compress_size,CRC32=f'{i.CRC:08x}',
            compression=i.compress_type,header_offset=i.header_offset) for i in archive.infolist()]
        save(RUN/'zip_index.json',dict(url=ZIP_URL,remote_size=remote.size,etag=http.etag,entries=entries))
    save(RUN/'index_fetch_manifest.json',dict(transferred_bytes=http.transferred,requests=http.records,
        readme_sha256=digest(RUN/'GOOGLE_DATA_README.md')))
    log('index_complete',entries=len(entries),remote_bytes=remote.size,transferred_bytes=http.transferred)
    print(json.dumps([i for i in entries if i['name'].endswith('initial_states.json') or
        ('exp_vals.h5' in i['name'] and '/mag_field_0/U_8/' in i['name'] and ('/5x5/' in i['name'] or '/6x6/' in i['name']))],indent=2))

def fetch(names):
    index=json.loads((RUN/'zip_index.json').read_text()); entries={i['name']:i for i in index['entries']}
    if not names or len(set(names))!=len(names): raise ValueError('Explicit unique entries required')
    if not all(n in entries and (n.endswith('/exp_vals.h5') or n.endswith('/initial_states.json')) for n in names):
        raise ValueError('Only indexed expectation values and initial state metadata may be fetched')
    if sum(entries[n]['compressed_bytes'] for n in names)>90_000_000: raise ValueError('Selected transfer exceeds90MB')
    http=BoundedHTTP(); remote=RangeZIP(http)
    if remote.size!=index['remote_size']: raise ValueError('ZIP changed since inventory')
    if index['etag'] and http.etag and index['etag']!=http.etag: raise ValueError('ZIP ETag changed')
    saved=[]
    with zipfile.ZipFile(remote) as archive:
        for name in names:
            info=archive.getinfo(name); expected=entries[name]
            if info.file_size>500_000_000 or info.compress_size>40_000_000: raise ValueError('Entry too large for bounded extraction')
            if info.file_size!=expected['bytes'] or f'{info.CRC:08x}'!=expected['CRC32']: raise ValueError('ZIP entry changed')
            path=RUN/'downloads'/name
            if not path.resolve().is_relative_to((RUN/'downloads').resolve()): raise ValueError('Unsafe ZIP path')
            if path.exists(): raise FileExistsError('Preserve previously fetched entry')
            payload=archive.read(name)  # zipfile verifies CRC of decompressed bytes.
            if len(payload)!=info.file_size: raise ValueError('Entry size mismatch')
            path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('xb') as f: f.write(payload)
            saved.append(dict(entry=name,relative_file=str(path.relative_to(RUN)),sha256=digest(path),CRC32=expected['CRC32'],bytes=len(payload)))
            log('entry_saved',entry=name,bytes=len(payload))
    token=hashlib.sha256(json.dumps(names).encode()).hexdigest()[:12]
    save(RUN/f'fetch_manifest_{token}.json',dict(files=saved,requests=http.records,transferred_bytes=http.transferred,remote_etag=http.etag))
    log('fetch_complete',files=len(saved),transferred_bytes=http.transferred)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('action',choices=('index','fetch'))
    parser.add_argument('--entry',action='append',default=[]); args=parser.parse_args()
    if args.action=='index': index()
    else: fetch(args.entry)
