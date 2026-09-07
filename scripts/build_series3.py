"""Reuse the existing Edukaizen formatter; generate draft HTML, never publish."""
import html, importlib.util, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'publication/edukaizen_series3'

def main():
    spec=importlib.util.spec_from_file_location('legacy_edukaizen_renderer',ROOT/'docs/build_wordpress_2d_cuprate_package.py')
    renderer=importlib.util.module_from_spec(spec); spec.loader.exec_module(renderer)
    pages=[]
    for p in sorted((BASE/'nl').glob('*.md')):
        meta,lines=renderer.parse_front_matter(p)
        assert meta['status']=='draft' and meta['language']=='nl'
        pages.append(dict(meta=meta,lines=lines,source=p))
    assert [p['meta']['part'] for p in pages]==list(range(10))
    assert len({p['meta']['slug'] for p in pages})==10
    out=BASE/'wordpress/nl'; out.mkdir(parents=True,exist_ok=True)
    preview=BASE/'preview'; preview.mkdir(exist_ok=True)
    manifest=[]
    for i,p in enumerate(pages):
        m=p['meta']; local_name=f'{i:02d}.html'; body=renderer.render_markdown(p['lines'])
        assert body.count('[latex syntax="display"]')==body.count('[/latex]')
        body='<p><strong>CONCEPT — nog niet gepubliceerd.</strong></p>\n'+body
        nav=['<a href="https://edukaizen.nl/hubbard-nighthawk-serie-3/">Serie 3</a>']
        for j,label in [(i-1,'Vorige'),(i+1,'Volgende')]:
            if 0<=j<len(pages): nav.append(f'<a href="https://edukaizen.nl/{pages[j]["meta"]["slug"]}/">{label}</a>')
        wp='<nav class="fh-series-nav">'+' | '.join(nav)+'</nav>\n'+body
        (out/local_name).write_text(wp,encoding='utf-8')
        # Offline preview displays the math source explicitly; WordPress renders it later.
        preview_body=re.sub(r'\[latex syntax="display"\](.*?)\[/latex\]',lambda z:'<pre class="math-source">'+html.escape(z.group(1).strip())+'</pre>',body,flags=re.S)
        localnav=' | '.join(f'<a href="{j:02d}.html">{label}</a>' for j,label in [(0,'Seriepagina'),(i-1,'Vorige'),(i+1,'Volgende')] if 0<=j<len(pages) and j!=i)
        doc='<!doctype html><html lang="nl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(m['title'])+'</title><style>body{font:18px/1.65 system-ui;max-width:850px;margin:3em auto;padding:0 1em;color:#202735}h1,h2{line-height:1.2}a{color:#1255aa}table{border-collapse:collapse;width:100%;font-size:.9em}td,th{padding:.5em;border-bottom:1px solid #ccd3dd;text-align:left}pre{overflow:auto;background:#f1f4f8;padding:1em}</style><nav>'+localnav+'</nav><main><h1>'+html.escape(m['title'])+'</h1>'+preview_body+'</main></html>'
        (preview/local_name).write_text(doc,encoding='utf-8')
        manifest.append(dict(part=i,title=m['title'],slug=m['slug'],status='draft',language='nl',proposed_url='https://edukaizen.nl/'+m['slug']+'/',source=str(p['source'].relative_to(ROOT)),wordpress_html=str((out/local_name).relative_to(ROOT)),preview=str((preview/local_name).relative_to(ROOT)),post_id=None,word_count=len(' '.join(p['lines']).split())))
    (BASE/'manifest.json').write_text(json.dumps(dict(status='DRAFT_NOT_PUBLISHED',series=3,language='nl',pages=manifest,existing_series_preserved=True),indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(dict(status='DRAFT_PACKAGE_BUILT',articles=9,hub=1,words=sum(p['word_count'] for p in manifest),published=0)))

if __name__=='__main__': main()
