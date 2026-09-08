"""Safe numeric TN checkpoints and resource-bounded scalar contraction."""
from pathlib import Path
import json
import numpy as np
import quimb.tensor as qtn

def save_tn(prefix,tn):
    prefix=Path(prefix);npz=prefix.with_suffix('.npz');meta=prefix.with_suffix('.json')
    if npz.exists() or meta.exists():raise FileExistsError('Preserve prior TN checkpoint')
    arrays={};tensors=[]
    for i,t in enumerate(tn.tensors):
        array=np.asarray(t.data)
        if not np.isfinite(array).all():raise ValueError('Nonfinite TN checkpoint')
        key=f'tensor_{i:03d}';arrays[key]=array
        tensors.append({'key':key,'inds':list(t.inds),'tags':list(t.tags),'shape':list(array.shape)})
    np.savez_compressed(npz,**arrays)
    metadata={'schema':'numeric-operator-tn-v1','sites':list(tn.sites),'exponent':float(tn.exponent),
              'tensors':tensors,'pickle_used':False}
    meta.write_text(json.dumps(metadata,indent=2)+'\n')

def load_tn(prefix):
    prefix=Path(prefix);meta=json.loads(prefix.with_suffix('.json').read_text())
    if meta['schema']!='numeric-operator-tn-v1':raise ValueError('Unknown tensor checkpoint schema')
    tensors=[]
    with np.load(prefix.with_suffix('.npz'),allow_pickle=False) as arrays:
        for item in meta['tensors']:
            array=arrays[item['key']]
            if list(array.shape)!=item['shape'] or not np.isfinite(array).all():raise ValueError('Invalid tensor array')
            tensors.append(qtn.Tensor(array,inds=item['inds'],tags=item['tags']))
    tn=qtn.TensorNetwork(tensors).view_as_(qtn.TensorNetworkGenVector,
        sites=tuple(meta['sites']),site_tag_id='I{}',site_ind_id='k{}')
    tn.exponent=meta['exponent']
    return tn

def bounded_contract(tn,*,max_elements=2**22,max_flops=2e9):
    tree=tn.contraction_tree(optimize='greedy',output_inds=())
    peak=float(tree.max_size());flops=float(tree.total_flops())
    if peak>max_elements or flops>max_flops:
        raise ValueError(f'Contraction resource guard: peak={peak}, flops={flops}')
    value=tn.contract(all,optimize=tree,output_inds=())
    if not np.isfinite(value) or abs(np.imag(value))>1e-9:raise ValueError('Invalid scalar contraction')
    return float(np.real(value)),{'max_elements':int(peak),'estimated_flops':flops}

def expectation_zero(tn):
    out=tn.copy()
    for q in tn.sites:out.add_tensor(qtn.Tensor([1.,0.,0.,1.],inds=(tn.site_ind(q),),tags=(f'RHO{q}',)))
    return bounded_contract(out)[0]
