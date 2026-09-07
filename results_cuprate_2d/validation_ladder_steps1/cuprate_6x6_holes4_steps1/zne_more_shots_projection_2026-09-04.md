# ZNE: meer shots, voorlopige schatting

Datum: 4 september 2026. Basis: job `dadhl2642tqs73atf07g` op IBM Phoenix, 6x6/72 logische qubits, t-only circuit, stap 1, tijd 0.1. Referentie: dezelfde MPS chi32-waarden als in de eerdere vergelijking.

De Nighthawk/ZNE-uitkomst is duidelijk beter dan de oude directe IBM-route. Binnen Phoenix verbetert ZNE vooral spin-z; charge en doublon liggen dicht bij de directe raw-uitkomst. De huidige gegevens wijzen op een beperkt aanvullend voordeel van alleen meer shots.

## Scenario bij gelijkblijvende ruis en instellingen

| shots per ruisfactor | charge RMSE | spin-z RMSE | doublon RMSE | status |
|---|---:|---:|---:|---|
| 128 | 0.137 | 0.150 | 0.057 | werkelijk gemeten |
| 512 | 0.129 | 0.142 | 0.051 | voorlopig model |
| 1024 | 0.128 | 0.140 | 0.050 | voorlopig model |
| 2048 | 0.127 | 0.140 | 0.050 | voorlopig model |
| 4096 | 0.127 | 0.139 | 0.049 | voorlopig model |

Bij 1024 in plaats van 128 shots is de statistische standaardfout circa sqrt(8)=2.83 maal kleiner. De volledige RMSE daalt in dit scenario minder omdat een resterende afwijking tegenover de referentie behouden blijft. Dit is geen empirisch aangetoonde ondergrens: er is maar een pilotrun.

Een vergelijking met 512 shots is een zinvolle budgetbeperkte controle van dit model. Voor toekomstige uitvoering blijven de oorspronkelijke budgetgrens en een nieuwe concrete opdracht tot submit leidend. Voor deze analyse zijn geen QPU-jobs ingediend.

## Berekening en controles

De opgeslagen `evs_noise_factors` bevatten per site n_up, n_down en dubbelbezetting voor ruisfactoren 1,3,5. Daaruit volgen de vier gezamenlijke kansen:

- p00 = 1 - n_up - n_down + d
- p10 = n_up - d
- p01 = n_down - d
- p11 = d

Alle kansen zijn niet-negatief. Voor elke factor is N=128 gebruikt. De gewogen lineaire extrapolatie van Z_up, Z_down en Z_up Z_down naar ruisfactor nul is gereconstrueerd met gewichten uit de factor-specifieke meetvarianties. De gereconstrueerde n_up/n_down-uitkomsten verschillen maximaal 1.34e-15 van de opgeslagen waarden; voor d is dat 6.67e-16.

Voor elke site is de shotvariantie door de lineaire extrapolatie gepropageerd, inclusief de covarianties tussen de twee bezettingen en de ZZ-term. De gemiddelde shotvariantie V128 is gebruikt voor:

`RMSE(N) = sqrt(max(0, RMSE(128)^2 - V128) + V128 * 128/N)`.

| component | charge | spin-z | doublon |
|---|---:|---:|---:|
| waargenomen RMSE bij 128 | 0.137214 | 0.149804 | 0.057279 |
| geschatte shotbijdrage, sqrt(V128) | 0.053278 | 0.055881 | 0.029511 |
| geschatte resterende afwijking | 0.126449 | 0.138991 | 0.049092 |

Deze resterende afwijking is een schatting uit een enkele run. Zij kan hardwarebias, onvolledige ZNE, referentiefout en niet-gemodelleerde fluctuaties bevatten. De gewichten zijn voor de projectie vastgezet op hun pilotwaarden; veranderingen van gewichten en kalibratie zijn niet meegenomen. Er is geen betrouwbaarheidsinterval voor deze projectie berekend.

De veel optimistischere veronderstelling dat de gehele fout als 1/sqrt(N) verdwijnt zou bij 1024 shots 0.049 / 0.053 / 0.020 geven. De uit de drie ruisniveaus afgeleide shotvarianties ondersteunen die veronderstelling hier niet.

IBM documenteert dat ZNE geen onbevooroordeelde uitkomst garandeert; extra shots lossen een verkeerde extrapolatie of blijvende ruis niet automatisch op. [IBM ZNE-documentatie](https://quantum.cloud.ibm.com/docs/en/guides/error-mitigation-and-suppression-techniques)

## Bewaarde gegevens

De [machineleesbare berekening](zne_more_shots_projection_2026-09-04.json) bevat alle scenario's, sitevarianties, referentieresiduen en aannames. Invoerbestanden:

- `ibm_phoenix_zne_estimator_s128_max5s/estimator_result.json`
- `ibm_phoenix_zne_estimator_s128_max5s/site_observables.csv`
- `mps_shallow_t_only_steps1/cuprate_2d_mps_site_observables_chi32.csv`

