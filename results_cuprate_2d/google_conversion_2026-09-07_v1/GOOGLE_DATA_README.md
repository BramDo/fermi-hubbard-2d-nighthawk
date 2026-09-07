# Programmable Digital Quantum Simulation of 2D Fermi-Hubbard Dynamics using 72 Superconducting Qubits
## Overview 

This repository contains data presented in the manuscript 
`Programmable Digital Quantum Simulation of 2D Fermi-Hubbard Dynamics using 72 Superconducting Qubits`. 

We use a nested folder structure, where each folder corresponds to a configuration of physical parameters. 
The parameters, as desribed in the paper are: 
- initial state: the state evolved by the Fermi Hubbard model (see Fig 1), one of
  - `center_hole`: a checkerboard background state with single holon at (or near) the middle of the lattice.
  - `distance_2_hole`: a checkerboard background state with two holons in the lattice with two lattice sites in between them.
  - `holon_stripe`: a checkerboard background state with a contiguous row of holons in one dimension of the lattice.
  - `singlets_with_distance_2_hole`: a background of singlet pairs across the lattice, with two holons with two lattice sites in between them.
- system size: lattice dimensions, one of
  - `4x4`
  - `5x5`
  - `5x6`
  - `6x6`
- magnetic flux across the system, either 
  - $\phi=0$ listed as `mag_field_0`
  - $\phi=\pi$ listed as `mag_field_pi`
- onsite term in the Fermi Hubbard model. e.g. $U=0$ is listed as `U_0`; likewise we compute $U=4, U=8$.
- number of Trotter layers in the quantum circuit, e.g $n_t=2$ is listed as `trotter_layers_2`.
  - note the majority of data presented in the paper comprise of 3 Trotter layers; specific details are included in the manuscript.

For example, the evolution of a $4\times4$ checkerboard state with a single hole at its center, with $\phi=\pi$ and $U=0$, through a quantum circuit consiting of 2 Trotter layers, is stored in 
```
programmable_simulation_fermi_hubbard/center_hole/4x4/mag_field_pi/U_0/trotter_layers_2
```

Within folders, data is structured in the following files:
- `shots.h5`: raw shots obtained from hardware. 
- `exp_vals.h5`: expectation values computed through several time dynamics simulation techniques.

## Initial states
The configuration of all initial states are listed in 
```
programmable_simulation_fermi_hubbard/initial_states.json
```
which you can load like 
```
import json
from pathlib import Path


initial_states = json.load(
    open(
        Path.cwd() / "programmable_simulation_fermi_hubbard" / "initial_states.json", 
        "r"
    )
)
```
Then, `initial_states` is a dictionary, whose keys are the states listed above, with a nested dictionary whose keys are system size.  
For example, `initial_states["holon_stripe"]["5x6"]` contains the configuration for the holon stripe state on a 5x6 lattice, which serves as the initial state for all simulations within `programmable_simulation_fermi_hubbard/holon_stripe/5x6`.

In each case, the configuration lists the $(x,y)$ coordinates at which `ups, downs, holons, doublons` are initialised, as well as `singlet_pairs`, i.e. pairs of sites which are jointly initialised into a singlet state.
These states are visualised in Fig 1 of the manuscript.

## Shots
Shots files can be unpacked, e.g. in Python
```python 
from pathlib import Path
import numpy as np
import pandas as pd
import h5py

def read_shots_from_h5(
    shots_h5_path: Path
):
    """
    Load shots data from file to dict.

    Parameters
    ----------
    h5_path : Path
        Path to shots data stored in h5 format.

    Returns
    -------
    dict
        Contains two fields: 
        `data` and `metadata` of shots corresponding to a timeseries.
        `data` is a dict whose keys are evolution times, and values
        are `np.array`s of bits, of dimension `n_shots, n_qubits`.
        `metadata` is a dict of fields describing the data, 
        e.g. the physical parameters of the simulation.
    """
    
    result_data = {}
    result_meta = {}

    with h5py.File(shots_h5_path.as_posix(), "r") as h5:

        g_data = h5["data"]

        for key in g_data.keys():
            dset = g_data[key]
            packed = dset[()]
            orig_rows, orig_cols = dset.attrs["original_shape"]

            # Unpack bits
            unpacked = np.unpackbits(packed, axis=-1)

            # Trim padded bits
            ## we had originally padded to use np packed arrays
            ## here we remove the padding
            unpacked = unpacked[:, :orig_cols]

            # Ensure uint8
            unpacked = unpacked.astype(np.uint8)

            # Register as float of evolution time
            result_data[float(key)] = unpacked

        # Recover metadata
        g_meta = h5["metadata"]
        for k, v in g_meta.attrs.items():
            result_meta[k] = v

    shot_data = {
        "data": result_data, 
        "metadata": result_meta
    }
    return shot_data


## TODO if you wish to inspect other data set(s), change path accordingly
path_to_data = Path.cwd() / "programmable_simulation_fermi_hubbard" / "center_hole" /"4x4" / "mag_field_pi" / "U_0" / "trotter_layers_2"

# Load shots into dictionary using given function
path_to_shots = path_to_data / "shots.h5"
shots_data = read_shots_from_h5(path_to_shots)
```

`shots_data` is a dict containing two entries: `data` and `metadata`. 

`data` is another dictionary, consisting of all shots corresponding to a single timeseries, i.e. the keys give the evolution time, with values containing arrays of shots.

Each element of each array is a single shot, e.g. `shots_data["data"][0.1][0]` is the first shot corresponding to `t=0.1` of the loaded timeseries.

First, inspect the shape of a shot array to see how many qubits and shots are in our dataset: 

```python
evolution_times = sorted(shots_data["data"])
n_shots, n_qubits = shots_data["data"][evolution_times[0]].shape
print(f"This timeseries contains {n_shots} shots on {n_qubits} qubits")
```

`shots_data` also contains `metadata`, which is shared for all points in the timeseries. 
This dictionary contains any pertinent physical parameters as described in the manuscript, for instance `onsite_term` represents the value of `U` in the Fermi-Hubbard model.


An important piece of metadata is the `qubit_order`: 
```python
qubit_order = shots_data["metadata"]["qubit_order"].tolist()
print(f"The order of qubits within shots is: {qubit_order}")
```
`qubit_order` will now contain a list of length `n_qubits`, whose elements tell us the mapping between qubit indices and the site and spin they represent in the Fermi-Hubbard model in the Jordan-Wigner encoding.
For example, a qubit with label `(1,3,up)` encodes the `up` spin of the site `(x=1, y=3)` on a 2D lattice.

Each shot array in `shots` corresponds to running a single circuit `n_shots` times. 
Upon measurement, if we see a `1` in a given qubit position, that registers that a fermion is detected at the corresponding fermionic mode.


### Example: sanity check state at early time
We wish to verify our initial state, using the shots data for the example configuration we loaded above. 
Note we did not measure at `t=0`, so the earliest evolution point is for `t=0.05`.
We can inspect that the state at early times intuitively agrees with our expectation.
Note these are independent measurements of the `up` and `down` modes of a given site, so we do not expect their occupation to sum to 1, but it should be in proportion to the initial state, with a short evolution.

The state we have prepared consists of 

- spin `up` at site `(0,0)`
    - so we expect the `up` mode to contain the majority of counts for `(0,0)`
- spin `down` at site `(0,1)`
    - so we expect the `down` mode to contain the majority of counts for `(0,1)`
- holon at site `(1,1)`, i.e. close to the center of the 4x4 lattice
    - so we expect neither `up` or `down` mode to have a high occupation. 


```python 
# Isolate the shot array for t=0.05
target_time = 0.05
shot_array = shots_data["data"][target_time]

# Inspect shot array 
n_shots, n_qubits = shot_array.shape

# Count how many `1`s appear in the shot array for each qubit index
rates = {
    i : float(
        shot_array.sum(axis = 0)[i]
        / n_shots
    ) 
    for i in range(n_qubits)
}

# Inspect the rate of measuring `1` on the specified qubits
# We expect the occupation rates to reflect our initial state.
for x,y in [(0,0), (0,1), (1,1),]:
    print(f"For site {x,y}, the rate of measuring 1 at t={target_time}:")
    for spin in ["up", "down"]:
        qubit_index = qubit_order.index(f"({x},{y},{spin})")
        occupation = round(rates[qubit_index], 2)
        print(f"\t {spin} \t {occupation}")
```

This should print the following, verifying our intuition at early times.
```
For site (0, 0), the rate of measuring 1 at t=0.05:
	 up 	 0.89
	 down 	 0.11
For site (0, 1), the rate of measuring 1 at t=0.05:
	 up 	 0.17
	 down 	 0.86
For site (1, 1), the rate of measuring 1 at t=0.05:
	 up 	 0.16
	 down 	 0.15
```

### Randomised compiling
Our circuits are compiled using randomised compilation. 
That is, we compile the same circuit several times, where each instance differs in the 1-qubit gates used to dress the 2-qubit gates in our original circuit.
In particular, we use 20 random instances, so to analyse the shots in order to produce the same error bars as in the manuscript, one must average the subsets of shots corresponding to the same compilation -- this procedure is described in Appendix E 10. 
The shots are grouped by compilation instance, where each instance is run for 10,000 shots, e.g. to isolate a single compilation, run `shot_array[:10000,:]`.

## Expectation Values
The `exp_vals.h5` file within each folder contains various expectation values computed through several time dynamics simulations: 
- raw hardware data.
- error-mitigated hardware data, i.e. following application of all mitigation steps described in Appendix E, is listed as `Mitigated` in the dataset.
- tensor networks, namely TDVP with varying maximum bond dimension $\chi$.

The `h5` files can be loaded into e.g. `pandas.DataFrame`s, with column names:
- `method`: time dynamics simulation technique used to compute this observable.
- `system_size`: number of rows and columns of the 2D lattice on which the Fermi-Hubbard model is defined.
- `onsite_term`: value of `U` in the Fermi-Hubbard Hamiltonian.
- `obs_type`: string uniquely identifying observables, e.g. `Z`, `doublon_sum`.
- `ev_time` : time the dynamics evolved to, at which this observable was measured.
- `site_coords`: `x,y` coordinates of the sites this observable refers to, if relevant.
- `spins`: whether the observable refers to the `up` or `down` modes of the given sites, if relevant. 
- `obs_val`: float value of the observable.
- `obs_err`: uncertainty on the value of the observable.
- Other columns can represent method-specific parameters, e.g. `max_bond_dimension` only refers to tensor network methods. 

These data underly the plots throughout the manuscript.
Each row of the dataframe refers to an expectation value of an observable.
The column `obs_type` specifies one of the following observables:
- `Z`: $\langle Z_{i} \rangle$ where $i$ indexes `site_coords` $(x,y)$ for `spins` $\sigma$.

- `ZZ`: $\langle Z_{i}  Z_{j} \rangle$ for `site_coords` $((x,y), (x^{\prime}, y^{\prime}))$ and `spins` $(\sigma, \sigma^{\prime})$.

### Exact data
For `U=0`, we provide `exact` expectation values, computed through fermionic linear optics, see Appendix E4. 
This data serves as the training data for the TFLO routine outlined in Appendix E3.

### Example
To load a set of expectation values from the same folder as `shots` above, run 

```python

import h5py
import pandas as pd 

def load_hdf_to_df(hdf_path: Path):
    
    hdf_file = h5py.File(hdf_path)
    
    loaded_df = pd.concat(
        pd.read_hdf(hdf_file.filename, key = k)
        for k in hdf_file.keys()
    )

    return loaded_df

exp_vals_path = path_to_data / "exp_vals.h5"

exp_vals = load_hdf_to_df(hdf_path=exp_vals_path)
```

For example, to visualise the `Z` observable over time on all sites of the $4\times4$ lattice:

```
import seaborn as sns

# Subselect some methods for a clear visualisation
target_methods = [
    "exact",
    'raw',
    'mitigated', 
    'TDVP chi=2048',
]

z_exp_vals = exp_vals[
    (exp_vals.obs_type == "Z")
    & (
        exp_vals.method.isin(target_methods)
    )
]

sns.relplot(
    data = z_exp_vals, 
    x = "ev_time", 
    y = "obs_val", 
    hue = "spins", 
    style = "method", 
    style_order = target_methods, 
    col = "site_coords", 
    col_order = sorted(z_exp_vals.site_coords.unique()),
    col_wrap = 4,
    kind = "line",
)
```

Which should produce a figure as below. 

![Dynamics of <Z> on all sites of 4x4 lattice](dynamics_Z.png)

Since $ | 0 \rangle $ encodes `no fermion` and $| 0 \rangle$ is the +1 eigenstate of $\langle Z \rangle $, we can immediately see the preparation of a holon at site (1,1), measuring $\langle Z_{(1,1) \uparrow} \rangle = \langle Z_{(1,1)\downarrow} \rangle = 1 $.
The effect of error mitigation is clear between the `raw` and `mitigated` lines.
Users can combine the expectation values to compute other observables of interest for each simulation technique. 
Most observables presented in the manuscript are computed from $\langle Z \rangle, \langle ZZ \rangle$. 