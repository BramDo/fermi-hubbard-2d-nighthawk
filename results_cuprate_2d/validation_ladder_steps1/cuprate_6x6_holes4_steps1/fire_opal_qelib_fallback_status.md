# 6x6 Fire Opal qelib Fallback Status

Fallback submitted on 2026-07-04 after the abstract/native Fire Opal route failed on a reserved `rzz` QASM gate name.

## Route

- output dir: `fire_opal_shallow_t_only_qelib_fallback`
- backend: `ibm_marrakesh`
- qasm basis: `qelib`
- qasm optimization level: 1
- shots main/readout: 1024 / 4096

## QASM Check

- parse ok: `True`
- contains `rzz`: `False`
- contains `xx_plus_yy`: `False`
- main two-qubit count/depth/depth: 312 / 10 / 25
- main QASM characters: 24258

## Submitted Actions

- main action id: `2331689`
- readout action id: `2331690`
- latest main status: `PENDING`
- latest readout status: `PENDING`
- latest API poll file timestamp: `2026-07-04 11:31:22` local time
- bounded `--wait` retrieve attempted after the site-ready signal, but no result payload was returned before timeout

No Fire Opal observables are available yet. Run `scripts/retrieve_cuprate_2d_6x6_fire_opal_shallow_t_only_qelib_fallback_wsl.ps1` to poll/retrieve, then `scripts/compare_cuprate_2d_6x6_shallow_t_only_qelib_fallback_vs_mps_wsl.ps1` after both actions succeed.

Claim boundary: this fallback is more Fire-Opal-compatible than the abstract/native submission, but it is less abstract and may give Fire Opal less optimization freedom.
