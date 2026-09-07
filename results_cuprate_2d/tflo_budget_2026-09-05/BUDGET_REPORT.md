# TFLO budgetcontrole: geen QPU-job ingediend

Actuele backend: ibm_phoenix, operationeel; 4 wachtende jobs bij controle.
Kalibratiedatum: 2026-09-05 17:25:23+02:00.

Plan: 10 instellingen x 8 expliciete twirls x 64 shots = 5120 shots, inclusief kalibratie. Alle 80 bevroren circuits passen op de actuele ISA; 928 controles geslaagd.

Shotuitvoering inclusief bestaande metingen, reset en standaard rep_delay: 0.145700 s. De standaard rep_delay is 1 microseconde; niet verlaagd voor deze schatting.

| Aantal interne subjobs | Raming inclusief opstartoverhead | Naar boven afgeronde planningswaarde |
|---|---:|---:|
| 1 | 2.146 s | 3 s |
| 2 | 4.146 s | 5 s |
| 3 | 6.146 s | 7 s |

IBM beschrijft circa 2 s overhead per interne subjob. Het aantal subjobs is vooraf niet bevestigd; de tabel is een scenarioanalyse, geen bovengrens of prijsopgave. Afronden is hier een planningskeuze, geen geverifieerde facturatieregel.

Een eventuele volgende run: een enkele job, harde max_execution_time=5, geen sessie/batch, geen automatische retry en geen backendwissel. Ingebouwde twirling blijft uit omdat de acht twirls al expliciet in de circuits staan. Geen extra ZNE/PEC of readout-learning toegevoegd. Ruwe bitstrings blijven vereist.

Er is nog geen nieuwe submissietoestemming verondersteld. De 5-secondenlimiet kan tot annulering leiden als de werkelijke overhead groter is. Deze controle gebruikt 0 QPU-seconden en toont geen mitigatieverbetering.

Bronnen: [IBM workload usage](https://quantum.cloud.ibm.com/docs/en/guides/estimate-job-run-time), [joblimieten](https://quantum.cloud.ibm.com/docs/en/guides/job-limits), [uitvoeringstijdlimiet](https://quantum.cloud.ibm.com/docs/en/guides/max-execution-time).
