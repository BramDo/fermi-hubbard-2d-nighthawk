"""Audit and package the public-data conversion; never launch a QPU job."""
import contextlib, gzip, hashlib, io, json, math, shutil, sys, unittest
from pathlib import Path
import numpy as np
import nbformat
from nbclient import NotebookClient
from convert_google_hubbard import ROOT, RUN, compute, digest, save

OWN=ROOT/'results_cuprate_2d/hardware_compact_tflo_2026-09-07_v1/analysis/summary.json'
CLASSICAL=ROOT/'results_cuprate_2d/classical_full_6x6_mps_T04_chi64_v1/summary.json'

def rms(a,b):
    return [math.sqrt(math.fsum((x[j]-y[j])**2 for x,y in zip(a,b))/len(a)) for j in range(3)]

def audit_and_compare(data=None):
    data=data or json.loads((RUN/'converted.json').read_text())
    own=json.loads(OWN.read_text()); classical=json.loads(CLASSICAL.read_text())
    refown=classical['result']['physical_means']
    rows=[]; convergence=[]; initial=[]; audit_max=0.
    for f in data['files']:
        assert digest(RUN/f['file'])==f['sha256']
        # Same continuous-time TDVP is explicitly shared across Trotter folders.
        # The 5x5 two-layer folder has no TDVP: use the matching three-layer folder,
        # with separate provenance. This is not an exact finite-circuit reference.
        ref_file=next(x for x in data['files'] if x['side']==f['side'] and x['folder_layers']==3)
        ref=next(r for r in ref_file['rows'] if r['group']=='TDVP' and r['chi']==2048)
        for r in f['rows']:
            p=r['physical_charge_spin_doublon']
            assert len(p)==f['side']**2 and r['clipped'] is False
            assert r['independent_max_abs']<1e-12
            metrics=rms(p,ref['physical_charge_spin_doublon'])
            check=np.sqrt(np.mean((np.array(p)-ref['physical_charge_spin_doublon'])**2,axis=0))
            audit_max=max(audit_max,max(abs(x-y) for x,y in zip(metrics,check)))
            if r['group']=='TDVP':
                assert abs(r['N']-f['side']*(f['side']-1))<2e-5
                if r['chi']==1024 and f['folder_layers']==3:
                    convergence.append(dict(side=f['side'],chi_from=1024,chi_to=2048,rms=metrics))
                continue
            rows.append(dict(case=f"Google {f['side']}x{f['side']} / {f['folder_layers']} lagen",group=r['group'],
                side=f['side'],sites=f['side']**2,N0=f['side']*(f['side']-1),N=r['N'],
                N_relative_error=(r['N']/(f['side']*(f['side']-1))-1),mean_D=r['mean_doublon'],
                spin_RMS=r['spin_profile_rms'],ref_D=ref['mean_doublon'],ref_spin_RMS=ref['spin_profile_rms'],
                rms_charge=metrics[0],rms_spin=metrics[1],rms_D=metrics[2],
                minimum_probability=r['minimum_local_probability'],reference='TDVP chi2048 (eigen Google-model)',
                reference_file=ref_file['file'],source_file=f['file'],time=.4,U=8,tprime=0.,
                profile=p,reference_profile=ref['physical_charge_spin_doublon']))
        for zero in f['time_zero']:
            holes=[list(c) for c,p in zip(zero['coordinates'],zero['physical_charge_spin_doublon']) if abs(p[0])<1e-5]
            assert holes==[[2,y] for y in range(f['side'])]
            initial.append(dict(side=f['side'],layers=f['folder_layers'],group=zero['group'],N=zero['N'],holes=holes,
                raw_hardware_at_t0=False))
    for r in own['target_rows']:
        p=r['physical_charge_spin_doublon']; metrics=rms(p,refown)
        assert max(abs(x-y) for x,y in zip(metrics,r['RMS_charge_spin_doublon']))<1e-12
        rows.append(dict(case='Ons 6x6 / '+r['circuit_arm'],group=r['arm'],side=6,sites=36,N0=32,N=r['N'],
            N_relative_error=r['N']/32-1,mean_D=r['mean_doublon'],spin_RMS=r['spin_profile_rms'],
            ref_D=math.fsum(p[2] for p in refown)/36,ref_spin_RMS=math.sqrt(math.fsum(p[1]**2 for p in refown)/36),
            rms_charge=metrics[0],rms_spin=metrics[1],rms_D=metrics[2],minimum_probability=r['min_onsite_probability'],
            reference='MPS chi64 (eigen model, niet geconvergeerd)',source_file=str(OWN.relative_to(ROOT)),
            reference_file=str(CLASSICAL.relative_to(ROOT)),time=.4,U=8,tprime=-.25,profile=p,reference_profile=refown))
    assert audit_max<1e-12
    return dict(rows=rows,convergence=convergence,initial_state_checks=initial,stdlib_RMS_check_max_abs=audit_max,
        metadata_audit=data['initial_states_metadata_audit'],source_hashes={str(OWN.relative_to(ROOT)):digest(OWN),str(CLASSICAL.relative_to(ROOT)):digest(CLASSICAL)},
        hardware_comparison_is_matched_problem=False,own_holdouts_pass=own['holdout_screen_pass'])

def artifact(result):
    chosen=[r for r in result['rows'] if r['group'] in ('mitigated','readout_tflo')]
    tidy=[]
    for r in chosen:
        for field,label in [('rms_charge','Lading'),('rms_spin','Spin'),('rms_D','Doublons')]:
            tidy.append({k:v for k,v in r.items() if k not in ('profile','reference_profile')} | dict(observable=label,RMS=r[field]))
    table=[{k:v for k,v in r.items() if k not in ('profile','reference_profile')} for r in chosen]
    for r in table:
        for k in ('N','mean_D','spin_RMS','ref_D','ref_spin_RMS','rms_charge','rms_spin','rms_D'): r[k]=round(r[k],5)
    source=dict(id='conversion',label='Google Zenodo 17881822 + eigen bewaarde hardwareanalyse',
        path='results_cuprate_2d/google_conversion_2026-09-07_v1/comparison.json',
        query=dict(language='python',engine='Python / NumPy / h5py',sql='from convert_google_hubbard import compute\nfrom package_google_conversion import audit_and_compare\nresult = audit_and_compare(compute())\nrows = result["rows"]',description='Z/ZZ naar charge, spin, doublons; elk profiel vergeleken met zijn eigen referentie.',
            tables_used=sorted({r['source_file'] for r in chosen}|{r['reference_file'] for r in chosen}),
            filters=['U=8','T=0.4','Google holon_stripe, flux0, 5x5/6x6, layers2/3','Eigen laatste original/compact TFLO; geen N-vervanging'],
            metric_definitions=['charge=1-(Zup+Zdown)/2','spin=(Zdown-Zup)/2','D=(1-Zup-Zdown+ZZ)/4','RMS=sqrt(mean_sites((estimate-reference)^2))']),
        href='https://zenodo.org/records/17881822')
    title='Google en onze Hubbard-resultaten in dezelfde eenheden'
    def md(i,text): return dict(id=i,type='markdown',body=text)
    blocks=[md('title','# '+title),md('summary','## Technische samenvatting\nDe omrekening is gelukt op de openbare Z/ZZ-data, niet via schattingen uit figuren. De nadruk in Googles paper ligt vaak op 5x5, maar de dataset bevat ook volledige lokale 6x6-profielen. In de geselecteerde gevallen liggen Googles gemitigeerde profielen dichter bij hun eigen klassieke referentie dan onze laatste TFLO-profielen bij onze chi64-referentie. Dit is beschrijvend: modellen, begintoestanden en referenties verschillen.'),
        md('definitions','## Zelfde grootheden, verschillende toestanden\nAlle rijen hebben U=8 en evolutietijd T=0.4, met hopping=1. Lading is n_up+n_down; spin is n_up-n_down; doublons is n_up*n_down. Google gebruikt in Eq. B1 al dezelfde spindefinitie: geen factor twee. N is de som van de lading; D is het gemiddelde per site; spin-RMS is de grootte van het lokale spinprofiel, niet zijn fout. De foutkolommen zijn RMS-afwijkingen per site ten opzichte van de eigen referentie.\n\nGoogle: holon stripe, t-prime=0, N0=20 op 5x5 en N0=30 op 6x6. Ons: vier gaten, t-prime=-0.25, N0=32 op 6x6. Delen door 25 of 36 verwijdert deze fysische verschillen niet.'),
        md('values','## De omgezette waarden liggen in dezelfde orde van grootte\nN, gemiddelde doublons en spin-RMS zijn direct uit lokale verwachtingswaarden berekend. Bij ons origineel ligt het gemiddelde D dicht bij chi64, maar een goed gemiddelde kan fouten op verschillende sites laten wegvallen. Nabijheid van N tot een bekend deeltjesaantal is evenmin onafhankelijke validatie, zeker na selectie of mitigatie.'),
        dict(id='values-table',type='table',tableId='values'),
        md('profiles','## De lokale afwijkingen geven een strenger beeld\nDe balken tonen drie RMS-afwijkingen per configuratie; lager betekent dichter bij de eigen referentie. Google 5x5 gebruikt TDVP chi2048, net als de Google 6x6-vergelijking; wij gebruiken nog niet geconvergeerde chi64. Vergelijk daarom niet als een gecontroleerde ranglijst of als bewezen absolute fouten. Zowel twee als drie Google-Trotterlagen staan erin om selectie van alleen de beste laagdiepte te vermijden.'),
        dict(id='rms-chart',type='chart',chartId='rms'),dict(id='rms-table',type='table',tableId='errors'),
        md('robustness','## Googles referentie is hier stabieler bij hogere chi\nBij 5x5 verandert chi1024 naar chi2048 de lokale lading/spin/doublons-RMS met ongeveer 0.0000042 / 0.0000142 / 0.0000086; bij 6x6 met 0.0000281 / 0.0002133 / 0.0000767. Dat is veel kleiner dan de hardwareafwijkingen, maar geen wiskundig foutcertificaat. Onze chi64 is nog niet geconvergeerd. Onze TFLO-holdoutcontrole is ook niet geslaagd en sommige gereconstrueerde lokale kansen zijn negatief; die zijn niet afgeknipt.'),
        md('methods','## De omzetting is algebraisch en onafhankelijk gecontroleerd\nUit n=(1-Z)/2 volgt D=(1-Z_up-Z_down+ZZ)/4. Alle sites en spinlabels zijn op volledigheid en uniciteit gecontroleerd. Een onafhankelijke oplossing voor de vier lokale bezettingskansen en een aparte RMS-somberekening reproduceren de omzetting. Er is geen tijdinterpolatie, clipping of vervanging van gemeten N toegepast.\n\nHet aparte initial_states.json bevat herhaalde, inconsistente configuraties. Het is daarom niet gebruikt om de begintoestand vast te leggen. De HDF5-labels en t=0-profielen tonen onafhankelijk een rij gaten en N=20/30. Deze t=0-ankers zijn geen rauwe hardwaremetingen. De 5x5-tweelaagsmap heeft geen eigen TDVP-groep: daar is expliciet de overeenkomstige continue-tijdreferentie uit de drielaagsmap gebruikt.'),
        md('uncertainty','## Dit is geen matched-accuracy of snelheidstest\nDe gepubliceerde marginale foutbalken bevatten geen volledige covariantie voor onze samengestelde grootheden; daarom zijn geen schijnbaar exacte betrouwbaarheidsintervallen toegevoegd. Google-mitigatie is overgenomen als gepubliceerd, niet opnieuw uit bitstrings gevalideerd. De verschillende Hamiltonianen, vullingen, Trottercircuits, shots en mitigatietraining verhinderen een rechtstreekse winnaarclaim. Deze selectie bestrijkt slechts U=8, T=0.4, holon stripe, nul flux, niet de hele paper.'),
        md('next','## Concreet vervolg: dezelfde opgave als benchmark\nEen eerlijke volgende test zou eerst het Google-model en dezelfde begintoestand reproduceren, dan dezelfde lokale fouten en een onafhankelijke mitigatie-holdout gebruiken. Voor onze eigen opgave blijft validatie van de TFLO-overdracht nodig. Er is nu geen nieuwe QPU-job of klassieke dynamicasimulatie gestart.\n\nOpen vraag: blijft het verschil bestaan bij hetzelfde model, dezelfde circuitbenadering, dezelfde nauwkeurigheid en volledig gemeten doorlooptijd?')]
    columns=lambda pairs:[dict(field=f,label=l,type='number' if f!='case' else 'string') for f,l in pairs]
    tables=[dict(id='values',title='Omgezette observabelen',dataset='values',sourceId='conversion',defaultSort=dict(field='case',direction='asc'),
        columns=columns([('case','Configuratie'),('N','N gemeten'),('N0','N doel'),('mean_D','D per site'),('ref_D','D referentie'),('spin_RMS','Spin-RMS'),('ref_spin_RMS','Spin referentie')])),
        dict(id='errors',title='RMS-afwijkingen per site',dataset='values',sourceId='conversion',defaultSort=dict(field='case',direction='asc'),
        columns=columns([('case','Configuratie'),('rms_charge','Lading'),('rms_spin','Spin'),('rms_D','Doublons')]))]
    chart=dict(id='rms',title='Lokale afwijkingen per configuratie',description='U=8, T=0.4; elke rij tegen eigen referentie; geen identieke fysische opgave',showDescription=True,
        type='bar',dataset='rms',sourceId='conversion',encodings=dict(x=dict(field='case',type='nominal'),y=dict(field='RMS',type='quantitative'),color=dict(field='observable',type='nominal')),
        options=dict(grouping='grouped'),palette=dict(kind='categorical',name='default'))
    return dict(surface='report',manifest=dict(version=1,surface='report',title=title,blocks=blocks,tables=tables,charts=[chart],sources=[source]),
        snapshot=dict(version=1,status='ready',generatedAt='2026-09-07',datasets=dict(values=table,rms=tidy)),sources=[source])

def main():
    result=audit_and_compare()
    if (RUN/'comparison.json').exists():
        assert json.loads((RUN/'comparison.json').read_text())==result
    else: save(RUN/'comparison.json',result)
    # This generated presentation may be corrected without touching source data.
    with (RUN/'artifact.json').open('w',encoding='utf-8') as f: json.dump(artifact(result),f,indent=2,allow_nan=False)
    cells=[nbformat.v4.new_markdown_cell('# Google Hubbard conversion audit\n\n## TL;DR\nPublished local Z/ZZ values can be converted to our definitions. The models are not identical; no advantage claim follows.'),
        nbformat.v4.new_markdown_cell('## Context and methods\nU=8, T=.4, no flux, holon stripe, 5x5/6x6, 2/3 layers. No parameter fitting, clipping, N substitution or interpolation. Reference differences and metadata limitations are preserved in the report.'),
        nbformat.v4.new_code_cell("from pathlib import Path\nimport sys, json, contextlib, io, unittest\nimport numpy as np\nroot=Path.cwd().resolve()\nassert (root/'convert_google_hubbard.py').exists()\nsys.path.insert(0,str(root))\nfrom convert_google_hubbard import RUN, compute\nfrom package_google_conversion import audit_and_compare\nfrom test_google_conversion import ConversionTests\nsuite=unittest.defaultTestLoader.loadTestsFromTestCase(ConversionTests)\nchecks=unittest.TextTestRunner(verbosity=2).run(suite)\nassert checks.wasSuccessful()"),
        nbformat.v4.new_markdown_cell('## Data\nRe-read all four selected HDF5 inputs. Original fetch manifests contain URL, CRC and SHA256. This cell is local analysis only; it does not fetch data or submit jobs.'),
        nbformat.v4.new_code_cell("with contextlib.redirect_stdout(io.StringIO()):\n    fresh=compute()\naudit=audit_and_compare(fresh)\nprint('Independent RMS max delta:',audit['stdlib_RMS_check_max_abs'])\nprint('Chi convergence:',audit['convergence'])\nprint('Initial metadata records:',audit['metadata_audit']['records'], 'distinct:',audit['metadata_audit']['distinct_configurations'])\narchived=audit_and_compare()\nassert audit==archived\nprint('Fresh HDF conversion matches archived comparison exactly')"),
        nbformat.v4.new_markdown_cell('## Results\nEach estimate is compared only to its own model reference; these are not all exact references.'),
        nbformat.v4.new_code_cell("import pandas as pd\ncols=['case','group','N','N0','mean_D','ref_D','spin_RMS','rms_charge','rms_spin','rms_D']\ndisplay(pd.DataFrame(audit['rows'])[cols])"),
        nbformat.v4.new_markdown_cell('## Takeaways\nThe 5x5 emphasis does not mean absence of quantitative 6x6 data. In this selected context Google local residuals are smaller against its own, more stable TDVP reference. Different hopping, holes, finite-circuit approximations and mitigation prohibit a matched-accuracy ranking. The external initial_states.json is inconsistent; HDF t=0 anchors show the nominal N=20/30, not raw hardware conservation. Covariance is unavailable, so aggregate confidence intervals are not invented.')]
    nb=nbformat.v4.new_notebook(cells=cells,metadata=dict(kernelspec=dict(name='python3',display_name='Python 3',language='python')))
    client=NotebookClient(nb,timeout=90,kernel_name='python3',resources={'metadata':{'path':str(ROOT)}})
    client.execute(); nbformat.write(nb,RUN/'google_conversion_audit.ipynb')
    for name in ['convert_google_hubbard.py','google_hdf_safe.py','test_google_conversion.py','package_google_conversion.py']:
        dest=RUN/'source_snapshot'/name
        with dest.open('xb') as f: f.write((ROOT/name).read_bytes())
    archive=[]
    for f in result['rows']:
        if not f['source_file'].endswith('.h5'): continue
        src=RUN/f['source_file']; dst=RUN/'compressed_inputs'/(str(src.relative_to(RUN/'downloads')).replace('/','__')+'.gz')
        if dst.exists(): continue
        dst.parent.mkdir(exist_ok=True)
        with src.open('rb') as inp, dst.open('xb') as raw:
            with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,filename='') as out: shutil.copyfileobj(inp,out)
        with gzip.open(dst,'rb') as inp: restored=hashlib.sha256(inp.read()).hexdigest()
        assert restored==digest(src)
        archive.append(dict(original=f['source_file'],gzip=str(dst.relative_to(RUN)),original_sha256=digest(src),gzip_sha256=digest(dst),gzip_bytes=dst.stat().st_size))
    save(RUN/'compressed_input_manifest.json',archive)
    save(RUN/'verification.json',dict(status='PASS',unit_tests=8,notebook_executed=True,notebook_errors=0,
        fresh_HDF_matches_archive=True,stdlib_RMS_max_abs=result['stdlib_RMS_check_max_abs'],lossless_input_mirrors=len(archive),
        physics_validated=False,new_QPU_jobs=0,new_classical_dynamics_jobs=0))
    print(json.dumps(dict(status='PACKAGED',rows=[{k:r[k] for k in ['case','group','N','mean_D','rms_charge','rms_spin','rms_D']} for r in result['rows']],convergence=result['convergence'])),flush=True)

if __name__=='__main__': main()
