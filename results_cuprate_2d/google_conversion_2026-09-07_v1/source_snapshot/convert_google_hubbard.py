"""Convert published Z/ZZ to our local observables, without asserting model identity."""
import hashlib,json,math,time
from pathlib import Path
import h5py
import numpy as np
from google_hdf_safe import read_group

ROOT=Path(__file__).resolve().parent
RUN=ROOT/'results_cuprate_2d/google_conversion_2026-09-07_v1'
DOWNLOADS=RUN/'downloads/programmable_simulation_fermi_hubbard'

def save(p,v):
    with p.open('x',encoding='utf-8') as f: json.dump(v,f,indent=2,allow_nan=False)
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def moments(zup,zdown,zz):
    zu,zd,pair=np.asarray(zup,float),np.asarray(zdown,float),np.asarray(zz,float)
    if zu.shape!=zd.shape or zu.shape!=pair.shape: raise ValueError('Moment shapes differ')
    return np.stack([1-(zu+zd)/2,(zd-zu)/2,(1-zu-zd+pair)/4],axis=-1)

def direct_probabilities(zu,zd,zz):
    # Independent linear solve for probabilities ordered00,01,10,11.
    matrix=np.array([[1,1,1,1],[1,1,-1,-1],[1,-1,1,-1],[1,-1,-1,1]],float)
    p=np.linalg.solve(matrix,np.stack([np.ones_like(zu),zu,zd,zz]))
    return p.T,np.stack([p[1]+p[2]+2*p[3],p[2]-p[1],p[3]],axis=-1)

def physical_row(data,side,at,chi=None):
    times=np.asarray(data['ev_time'],float); selected=np.isclose(times,at,rtol=0,atol=1e-12)
    if chi is not None: selected &= np.asarray(data['max_bond_dimension'],int)==chi
    indices=np.flatnonzero(selected)
    if not len(indices): return None
    expected={(x,y) for x in range(side) for y in range(side)}
    z={}; zz={}; error={}; keys=set(); metadata={}
    for key in ('method','initial_state','system_dims','onsite_term','n_layers','mag_field'):
        values=sorted(set(str(data[key][i]) for i in indices))
        if len(values)!=1: raise ValueError('Mixed metadata '+key)
        metadata[key]=values[0]
    if metadata['system_dims']!=f'{side}x{side}' or metadata['onsite_term']!='8' or metadata['mag_field']!='0':
        raise ValueError('Unexpected physical configuration')
    for i in indices:
        kind=str(data['obs_type'][i]); coords=tuple(tuple(map(int,c)) for c in data['site_coords'][i]); spins=tuple(map(str,data['spins'][i]))
        key=(kind,coords,spins)
        if key in keys: raise ValueError('Duplicate observable row')
        keys.add(key)
        value=float(data['obs_val'][i]); err=float(data['obs_err'][i])
        if not math.isfinite(value) or any(c not in expected for c in coords): raise ValueError('Invalid value/site coordinate')
        if kind=='Z':
            if len(coords)!=1 or len(spins)!=1 or spins[0] not in ('up','down'): raise ValueError('Invalid Z labels')
            q=(coords[0],spins[0]); z[q]=value; error[q]=err if math.isfinite(err) else None
        elif kind=='ZZ' and coords[0]==coords[1] and set(spins)=={'up','down'}:
            if coords[0] in zz: raise ValueError('Duplicate onsite ZZ')
            zz[coords[0]]=value; error[coords[0]]=err if math.isfinite(err) else None
    if set(z)!={(c,s) for c in expected for s in ('up','down')} or set(zz)!=expected:
        raise ValueError('Missing local Z or onsite ZZ values')
    coords=sorted(expected); zu=np.array([z[c,'up'] for c in coords]); zd=np.array([z[c,'down'] for c in coords]); pair=np.array([zz[c] for c in coords])
    profile=moments(zu,zd,pair); probs,independent=direct_probabilities(zu,zd,pair)
    delta=float(np.max(np.abs(profile-independent)))
    if delta>1e-12: raise ValueError('Independent probability conversion mismatch')
    spin=profile[:,1]; phases=np.array([(-1)**(x+y) for x,y in coords])
    return dict(time=float(at),metadata=metadata,chi=chi,sites=side*side,coordinates=coords,
        physical_charge_spin_doublon=profile.tolist(),N=float(profile[:,0].sum()),mean_charge=float(profile[:,0].mean()),
        N_up=float(((1-zu)/2).sum()),N_down=float(((1-zd)/2).sum()),mean_doublon=float(profile[:,2].mean()),
        spin_profile_rms=float(np.sqrt(np.mean(spin**2))),staggered_spin=float(np.mean(phases*spin)),
        minimum_local_probability=float(probs.min()),clipped=False,independent_max_abs=delta,
        source_rows=len(indices),local_Z_rows=len(z),onsite_ZZ_rows=len(zz),
        primitive_marginal_errors=[dict(site=c,z_up=error[c,'up'],z_down=error[c,'down'],zz=error[c]) for c in coords],
        aggregate_uncertainty_available=False,aggregate_uncertainty_note='Published marginal obs_err lacks inter-observable covariance; no independent-noise assumption or certified error bar is invented.')

def metadata_audit():
    path=DOWNLOADS/'initial_states.json'; data=json.loads(path.read_text()); rows=[]; identities=[]
    for state,sizes in data.items():
        for shape,config in sizes.items():
            a,b=map(int,shape.split('x'))
            coords=[tuple(c) for k in ('ups','downs','holons','doublons') for c in config[k]]
            coords += [tuple(c) for pair in config['singlet_pairs'] for c in pair]
            invalid=[list(c) for c in coords if not(0<=c[0]<a and 0<=c[1]<b)]
            rows.append(dict(state=state,shape=shape,covered_unique_sites=len(set(coords)),expected_sites=a*b,
                out_of_bounds=invalid,complete_and_in_bounds=len(set(coords))==a*b and not invalid,
                expected_N_from_declared_states=len(config['ups'])+len(config['downs'])+2*len(config['doublons'])+2*len(config['singlet_pairs'])))
            identities.append(json.dumps(config,sort_keys=True))
    return dict(source_sha256=digest(path),records=len(rows),distinct_configurations=len(set(identities)),rows=rows,
        action='Do not use this JSON to assert preparation identity; audit time-zero values and case metadata separately. This is an exported-metadata issue, not proof that the experimental measurements are wrong.')

def analyze_file(path):
    side=int(path.parts[-5].split('x')[0]); folder_layers=int(path.parts[-2].split('_')[-1]); rows=[]; inventory=[]; initial=[]
    with h5py.File(path,'r') as f: groups=list(f.keys())
    for group in groups:
        if group not in ('raw','mitigated','TDVP'):
            inventory.append(dict(group=group,used=False,reason='Exact FLO is U0 training data, not an exact U8 reference; may be an empty HDF placeholder.'))
            continue
        d=read_group(path,group)
        inventory.append(dict(group=group,rows=len(d['obs_val']),columns=list(d),
            methods=sorted(set(map(str,d['method']))),onsite_terms=sorted(set(map(str,d['onsite_term']))),
            times=sorted(set(map(float,d['ev_time'])))))
        if group not in ('raw','mitigated','TDVP'): continue
        chis=sorted(set(map(int,d['max_bond_dimension']))) if group=='TDVP' else [None]
        for chi in chis:
            row=physical_row(d,side,.4,chi)
            if row is not None:
                row.update(group=group,folder_layers=folder_layers,source_file=str(path.relative_to(RUN))); rows.append(row)
        # All starting values are audited but never assumed to be raw shots at t=0.
        zero=physical_row(d,side,0.,max(chis) if group=='TDVP' else None)
        if zero is not None:
            zero.update(group=group,folder_layers=folder_layers)
            zero['near_Fock_initial_profile']=bool(np.max(np.minimum(np.abs(np.array(zero['physical_charge_spin_doublon'])[:,0]),np.abs(np.array(zero['physical_charge_spin_doublon'])[:,0]-1)))<1e-5)
            initial.append(zero)
    return dict(file=str(path.relative_to(RUN)),sha256=digest(path),side=side,folder_layers=folder_layers,inventory=inventory,rows=rows,time_zero=initial)

def compute():
    inputs=sorted(DOWNLOADS.glob('holon_stripe/*/mag_field_0/U_8/trotter_layers_*/exp_vals.h5'))
    if len(inputs)!=4: raise ValueError('Expected four explicitly selected files')
    files=[]
    for path in inputs:
        result=analyze_file(path); files.append(result)
        print(json.dumps(dict(file=result['file'],rows=[{k:r[k] for k in ('group','chi','time','N','mean_doublon','spin_profile_rms','minimum_local_probability')} for r in result['rows']])),flush=True)
    comparisons=[]; layer_checks=[]
    for f in files:
        tdvp=[r for r in f['rows'] if r['group']=='TDVP']
        if tdvp:
            ref=max(tdvp,key=lambda r:r['chi']); refarr=np.array(ref['physical_charge_spin_doublon'])
            for row in f['rows']:
                arr=np.array(row['physical_charge_spin_doublon']); diff=arr-refarr
                comparisons.append(dict(side=f['side'],folder_layers=f['folder_layers'],group=row['group'],chi=row['chi'],
                    reference_group='TDVP',reference_chi=ref['chi'],reference_is_exact=False,
                    RMS_charge_spin_doublon=np.sqrt(np.mean(diff**2,axis=0)).tolist(),
                    max_abs_charge_spin_doublon=np.max(np.abs(diff),axis=0).tolist()))
    for side in (5,6):
        first=next(f for f in files if f['side']==side and f['folder_layers']==2)
        second=next(f for f in files if f['side']==side and f['folder_layers']==3)
        for group in ('raw','mitigated','TDVP'):
            a=[r for r in first['rows'] if r['group']==group]; b=[r for r in second['rows'] if r['group']==group]
            for row in a:
                other=next((x for x in b if x['chi']==row['chi']),None)
                if other:
                    delta=float(np.max(np.abs(np.array(row['physical_charge_spin_doublon'])-np.array(other['physical_charge_spin_doublon']))))
                    layer_checks.append(dict(side=side,group=group,chi=row['chi'],layers2_vs3_max_abs=delta,
                        metadata_layers=[row['metadata']['n_layers'],other['metadata']['n_layers']]))
    return dict(status='CONVERTED_WITH_MODEL_AND_METADATA_CAVEATS',files=files,comparisons_to_own_TDVP=comparisons,
        initial_states_metadata_audit=metadata_audit(),layer_folder_checks=layer_checks,
        spin_convention='Google EqB1 and ours both n_up-n_down; no factor2.',
        model_identity_with_our_experiment=False,
        why_not_same_problem=['Google nearest-neighbour Hamiltonian versus our t_prime=-.25.',
            'Google nominal holon stripe versus our four-hole stripe_neel; starting-state metadata requires auditing.',
            '5x5 is not6x6; per-site normalization does not remove finite-size or filling effects.',
            'Google TDVP reference is not automatically the same finite-circuit reference as our MPS chi64.'])

if __name__=='__main__':
    output=RUN/'converted.json'
    if output.exists(): raise FileExistsError('Preserve existing conversion')
    started=time.perf_counter(); result=compute(); result['seconds']=time.perf_counter()-started; save(output,result)
    print(json.dumps(dict(status=result['status'],seconds=result['seconds'],initial_state_distinct=result['initial_states_metadata_audit']['distinct_configurations'])),flush=True)
