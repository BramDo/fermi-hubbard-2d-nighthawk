# Compacte TFLO-job voltooid en geanalyseerd

- Job: `dae5gat1ierc738lmg10`, backend `ibm_phoenix`, status DONE.
- Werkelijk QPU-verbruik: **4 seconden**, providerlimiet 5 seconden.
- Ontvangen en geverifieerd: 80 circuits x 64 shots = 5120; 512 per instelling.
- Precies een indieningspoging. De plan-level lock blijft staan; niet herhalen.

## Resultaat volgens het vooraf vastgelegde protocol

Gepoolde U=8-Pauli-MSE: raw **0.264518**, TFLO **0.033645**, goedkope
klassieke U=0-FLO-voorspelling **0.033533**. De TFLO-winst boven raw is
statistisch duidelijk in de sampling/bootstrapcontrole; de extra winst
boven de klassieke controle niet. Geen quantum-advantageclaim.

U=8,T=0.2: 141/512 shots behouden; spin-RMSE 0.5319 -> 0.0869.
U=8,T=0.4: 190/512 shots behouden; spin-RMSE 0.4226 -> 0.2051.
400 van 400 bootstrapreplicaties bruikbaar. Geen filterherselectie of clipping.

Fysische kanttekening: een TFLO-doublonschatting bij T=0.2 is -0.01948,
buiten het toegestane [0,1]. Het interval [-0.03749, 0.03710] bevat nul.
Dit is behouden zonder clipping; zie `PHYSICAL_BOUNDS_NOTE.md`.

De ruwe MSE is beschrijvend 16.8% lager dan bij de oude job, maar de uiteindelijke
TFLO-MSE is niet verbeterd (oud 0.030717, nieuw 0.033645). Verschillende jobs
zijn door mogelijke hardwaredrift geen causaal A/B-experiment.

## Bewaard

- `approved_intent.json`: deze nieuwe, afzonderlijke toestemming.
- `job_receipt.json`, `provider_budget_verification.json`, `provider_metrics.json`.
- `bound_inputs/`, `provider_inputs/`, `provider_result_complete.json`, `raw_bitstrings.json`.
- `primary_analysis/RESULT_REPORT.md`: volledige uitkomst en grenzen.
- `PHYSICAL_BOUNDS_NOTE.md`: toelichting op de onfysische puntschatting.
- `primary_analysis/`: protocolverwijzing, vaste fit, bootstrapreplicaties en broncode.
- `final_audit/`: 35 eindcontroles, 207 geverifieerde artifacthashes, 26 tests en historische vergelijking.

De status 'analysis pending' in de onveranderde ophaalmetadata beschrijft het
moment van downloaden; de primaire analyse hierboven is inmiddels voltooid.
De oude strikte analyse en oude indieningslock zijn ongewijzigd bewaard.
