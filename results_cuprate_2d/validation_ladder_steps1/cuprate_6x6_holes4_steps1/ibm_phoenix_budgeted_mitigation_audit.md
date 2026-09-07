# IBM Phoenix budgeted mitigation audit

Date: 2026-09-04  
Backend: `ibm_phoenix` (IBM Nighthawk r2, 120 qubits)  
Account: `qiskit-runtime-q9`  
Problem: 6x6 open-boundary 2D Hubbard model, 4 holes, 72 spin orbitals, `U/t=8`, `t'/t=-0.25`, `dt=0.1`, one Trotter step, stripe-Neel initial state.  
Circuit family: `number_preserving_t_only`.

## Execution ledger

| route | primitive | job ID | shots requested | hard maximum | final status | billed QPU seconds | list-price estimate* |
|---|---|---|---:|---:|---|---:|---:|
| direct raw plus readout calibrations | SamplerV2 | `dadgm5dnj4cs73ads6ng` | 128 per pub, 3 pubs | 5 s | DONE | 3 | USD 4.80 |
| XY4 plus gate twirling | SamplerV2 | `dadhca3dd5gc73d7b8vg` | 128 per pub, 3 pubs | 5 s | DONE | 3 | USD 4.80 |
| ZNE | EstimatorV2 | `dadhl2642tqs73atf07g` | 128 default | 5 s | DONE | 3 | USD 4.80 |
| PEC | EstimatorV2 | `dadhlnlnj4cs73adtc3g` | 128 default | 5 s | DONE | 3 | USD 4.80 |
| Fire Opal validation | none | none | 0 | n/a | backend unsupported | 0 | USD 0.00 |
| **total** |  |  |  |  |  | **12** | **USD 19.20** |

\* Conservative arithmetic at the IBM Pay-As-You-Go list price used for this audit, USD 1.60 per QPU second. The provider billing record is authoritative.

The PEC and ZNE jobs together used 6 billed QPU seconds, corresponding to an estimated USD 9.60 at that rate.

## Circuit identity and scope

- The direct and XY4 Sampler runs used the same transpiled main circuit: depth 249, 777 CZ gates, two-qubit depth 89. Instruction SHA-256: `04ce79265b36fdf43237072ee0093d39aa9f50354128cab275cadf4eb138847e`.
- Their common classical-bit to physical-qubit measurement map has SHA-256 `f1157e328d04018410a01e672d20ca50e924b0f312ac1d3acc9548a0c8795dd6`.
- The PEC and ZNE Estimator runs used the same unmeasured ISA circuit: depth 248, 777 CZ gates, two-qubit depth 89, 108 diagonal site observables. Instruction SHA-256: `fd517e4aa1b18e44cc5291fdcaeed2c7248eb42c74c59563beab1e63cbb2478d`.
- Estimator QPY SHA-256: PEC `65c0739c7dd26d9c882aa55fed80d4fcf7c44fd79bef2341af28ac9473e81130`; ZNE `fff2cbf4414b648e18d5801be662a8251912235f5282d1f1ccbc7e6b5974bdb7`.
- Observables are `n_up`, `n_down`, and double occupancy for all 36 sites; charge, spin-z and hole density are derived from those values.
- Measurement mitigation was disabled for both Estimator jobs to contain cost and keep the comparison with the valid direct raw profile interpretable.

## Mitigation settings

ZNE:

- gate-folding amplifier;
- noise factors `1, 3, 5`;
- linear extrapolation with fallback, extrapolated to noise factor `0`;
- Runtime result contains raw noise-factor values, extrapolated values, standard deviations and ensemble standard deviations for all 108 observables;
- Runtime metadata: 128 shots, target precision `0.08838834764831843`, one randomization.

PEC:

- probabilistic error cancellation enabled, ZNE disabled;
- maximum overhead `2.0`, automatic noise gain;
- fresh layer-noise learning limited to one unique layer, pair depths `0, 1, 2`, two randomizations of 32 shots;
- conservative pre-submission upper bound: 1984 shots, of which 1728 for layer learning and 256 target shots;
- Runtime metadata: 256 effective shots, four randomizations, learned total noise overhead `21.73317728281183`, three mitigated layers, one unique mitigated layer with overhead `2.7906652269184486`.

PEC and ZNE were deliberately submitted as separate Estimator jobs because Runtime 0.48 rejects simultaneous PEC and ZNE activation.

## Comparison with MPS chi=32

All rows were normalized to the same 36 sites at step 1, time 0.1.

| profile | charge RMSE | spin-z RMSE | doublon RMSE | total charge | total spin-z |
|---|---:|---:|---:|---:|---:|
| direct raw | 0.137371 | 0.215794 | 0.056048 | 31.140625 | -0.234375 |
| XY4 plus twirling, raw | 0.225324 | 0.333308 | 0.114316 | see route CSV | see route CSV |
| XY4 plus twirling, readout corrected | 0.223382 | 0.318909 | 0.117927 | see route CSV | see route CSV |
| ZNE | 0.137214 | 0.149804 | 0.057279 | 32.436979 | -0.705717 |
| PEC | 0.482026 | 0.125025 | 0.171049 | 48.580446 | 0.033146 |

ZNE improves the spin-z RMSE relative to direct raw and is essentially tied on charge and doublon RMSE. PEC improves spin-z RMSE but fails badly for charge and double occupancy at this shot budget. Its total charge and several site occupations are unphysical, consistent with the very large learned quasi-probability overhead and high estimator variance. XY4 plus twirling worsened all three reported RMSEs.

## Validation notes

- The first direct run's raw counts and raw observable profile are valid.
- Its separately transpiled all-zero/all-one readout calibrations landed on different physical qubits from the main circuit. Therefore its `readout_corrected` profile is invalid and must not be used. This is recorded in `ibm_phoenix_budgeted_s128_max5s/READOUT_CALIBRATION_WARNING.md`.
- The later XY4 run enforces layout-matched readout calibration and records `readout_layout_matched=true`.
- Exact particle-sector survival was 7/128 for direct raw and 1/128 for XY4 plus twirling, so sector postselection is too data-starved here to support a strong comparison.
- Fire Opal 12.1 device discovery did not list `ibm_phoenix`; validation and execution were not attempted, credentials were not printed, and zero Fire Opal quantum seconds were used.
- These results concern diagonal site observables only. They do not measure off-diagonal d-wave pairing and do not establish superconductivity or quantum advantage.

## Preserved artifacts

- `ibm_phoenix_pec_estimator_s128_max5s/plan.json`: full circuit summary, observable definitions, options, shot accounting and circuit hashes.
- `ibm_phoenix_pec_estimator_s128_max5s/submission_receipt.json`: job identity, timestamps, status, software versions and provider-reported QPU charge time.
- `ibm_phoenix_pec_estimator_s128_max5s/estimator_result.json`: full PEC result arrays and metadata.
- `ibm_phoenix_pec_estimator_s128_max5s/site_observables.csv`: all 36 normalized site rows.
- `ibm_phoenix_zne_estimator_s128_max5s/plan.json`: full circuit summary, observable definitions, options, shot accounting and circuit hashes.
- `ibm_phoenix_zne_estimator_s128_max5s/submission_receipt.json`: job identity, timestamps, status, software versions and provider-reported QPU charge time.
- `ibm_phoenix_zne_estimator_s128_max5s/estimator_result.json`: raw and extrapolated ZNE arrays plus uncertainties and metadata.
- `ibm_phoenix_zne_estimator_s128_max5s/site_observables.csv`: all 36 normalized site rows.
- `observable_comparison_ibm_phoenix_pec_zne_s128_vs_mps/`: normalized combined comparison, summaries, RMSE table and report.
- `ibm_phoenix_pec_zne_artifact_sha256.csv`: SHA-256 manifest for the runner, wrapper, PEC/ZNE results and comparison files.

