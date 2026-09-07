# TFLO 3x3: hardwarejob voltooid, analyse gestopt

Job: dae3rou42tqs73au78d0 op ibm_phoenix. Status DONE.
Werkelijk verbruik: **4 QPU-seconden**; providerlimiet 5 seconden bevestigd.
Alle 80 scalar PUBs x 64 shots = **5120 shots** ontvangen. Providerinputs en metadata zijn gecontroleerd.

## Uitkomst van de vooraf vastgelegde analyse

Strikte selectie op N_up=N_down=4 behoudt 374/5120 shots (7.30%): slechts 27-50 per instelling. Drie instellingen halen het vooraf gekozen minimum van 32 niet. De TFLO-fit is daarom niet uitgevoerd. Het filter en de minimumdrempel zijn niet achteraf aangepast.

| Instelling | Behouden / 512 | Onder minimum 32 |
|---|---:|---|
| train_U0_T0 | 36 | nee |
| train_U0_T0.1 | 30 | ja |
| train_U0_T0.2 | 42 | nee |
| train_U0_T0.3 | 28 | ja |
| train_U0_T0.4 | 39 | nee |
| train_U0_T0.5 | 40 | nee |
| flo_holdout_U0_T0.15 | 50 | nee |
| flo_holdout_U0_T0.35 | 27 | ja |
| interacting_holdout_U8_T0.2 | 45 | nee |
| interacting_holdout_U8_T0.4 | 37 | nee |

## Interagerende referentiepunten: ruwe meetfout

| Tijd | Charge RMSE | Spin RMSE | Doublon RMSE |
|---|---:|---:|---:|
| 0.2 | 0.1840 | 0.5829 | 0.1725 |
| 0.4 | 0.1572 | 0.4792 | 0.1323 |

Dit zijn fouten ten opzichte van dezelfde eindige ideale circuits. Spin is n_up-n_down, niet S_z. Retentie is geen fidelity; minder chargefout na sectorselectie alleen is geen bewijs van correcte dynamica.

## Bewaard en vervolggrens

De exacte aangeleverde en teruggelezen provider-circuits, opties, 5120 ruwe bitstrings, volledige providerresultaten, metrics, capverificatie, job-ID en indieningsblokkering zijn opgeslagen. Zes offline veiligheidstests en 80 QPY-herlaadchecks gingen aan de eenmalige submissie vooraf. HTTP-retries waren voor indiening uitgeschakeld.

Geen tweede job gestart. Geen TFLO-verbetering of quantum advantage aangetoond. Een volgende analyse kan een vooraf beschreven versoepeld filter uitsluitend met U=0-kalibratie/validatie toetsen op deze bestaande data, maar dat is niet uitgevoerd en mag de mislukte bevroren analyse niet vervangen.
