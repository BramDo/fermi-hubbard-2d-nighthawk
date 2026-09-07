# Fire Opal shallow abstract v2 submit status

Status: submit attempted, but no Fire Opal action was created.

Date: 2026-07-04

## Attempt

Command:

`scripts/submit_cuprate_2d_6x6_fire_opal_shallow_t_only_abstract_v2_wsl.ps1`

Target:

- backend: `ibm_marrakesh`
- route: `fire_opal_shallow_t_only_abstract_v2`
- circuit family: `number_preserving_t_only`
- shots: `1024`
- readout shots: `4096`

## Result

The local QASM plan and manifest were written successfully:

- `fire_opal_plan.json`
- `fire_opal_qasm_manifest.json`
- `qasm/main_00_main.qasm`

The Fire Opal submit call failed before returning an action id:

`qctrlclient.exceptions.GraphQLQueryError: You have exceeded the maximum number of API calls per day. For increased rate limits, reach out to the Q-CTRL team at support@q-ctrl.com.`

No `fire_opal_submitted_jobs.json` file exists in this directory, so there is no recorded Fire Opal action id to retrieve.

## Local v2 QASM checks

- parse ok: true
- main circuit depth: 8
- two-qubit count: 156
- two-qubit depth: 5
- contains reserved `rzz`: false
- contains native alias `fo_rzz`: true

## Retry boundary

Do not retry repeatedly while the Q-CTRL daily API-call limit is active. A later retry should use the same submit wrapper after the daily limit resets or after Q-CTRL rate limits are increased.

## Interpretation boundary

This is not hardware output. The v2 input is prepared and locally parse-validated, but no Fire Opal hardware result exists from this attempt.
