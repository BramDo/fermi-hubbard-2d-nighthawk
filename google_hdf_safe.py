"""Read fixed-format pandas HDF5 blocks with a restricted NumPy-only unpickler."""
import io,pickle
import h5py
import numpy as np

class ArrayUnpickler(pickle.Unpickler):
    def find_class(self,module,name):
        allowed={('numpy','ndarray'):np.ndarray,('numpy','dtype'):np.dtype}
        for prefix in ('numpy.core.multiarray','numpy._core.multiarray'):
            allowed[prefix,'_reconstruct']=np._core.multiarray._reconstruct
            allowed[prefix,'scalar']=np._core.multiarray.scalar
        if (module,name) not in allowed:
            raise pickle.UnpicklingError('Forbidden pickle global '+module+'.'+name)
        return allowed[module,name]

def read_group(path,key):
    with h5py.File(path,'r') as file:
        g=file[key]
        if g.attrs.get('pandas_type')!=b'frame': raise ValueError('Only fixed DataFrame HDF groups supported')
        n=len(g['axis1']); columns=[v.decode() for v in g['axis0'][()]]; out={}
        if n>1_000_000 or len(columns)>40: raise ValueError('Unexpected frame dimensions')
        for i in range(int(g.attrs['nblocks'])):
            items=[v.decode() for v in g[f'block{i}_items'][()]]
            ds=g[f'block{i}_values']
            if ds.dtype.kind=='O':
                if ds.shape!=(1,): raise ValueError('Unexpected object storage')
                payload=bytes(ds[0])
                if len(payload)>100_000_000: raise ValueError('Object block too large')
                data=ArrayUnpickler(io.BytesIO(payload)).load()
            else: data=ds[()]
            if not isinstance(data,np.ndarray) or data.shape!=(n,len(items)): raise ValueError('HDF block shape mismatch')
            for j,name in enumerate(items):
                if name in out: raise ValueError('Duplicate HDF column')
                out[name]=data[:,j]
        if set(out)!=set(columns): raise ValueError('Missing HDF columns')
        return out
