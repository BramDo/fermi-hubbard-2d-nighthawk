# Vergelijking Edukaizen Hubbard 2D met Nighthawk

Controle uitgevoerd: 4 september 2026.

Phoenix levert voor dezelfde 6x6 circuitdiagnose duidelijk lagere fouten dan de oude directe Marrakesh-run. Ten opzichte van de eerdere Fire Opal Fez-route heeft Phoenix met ZNE lagere spin-z- en doublonfouten, maar een iets hogere ladingsfout. PEC geeft de laagste spin-z-puntschatting in deze selectie, terwijl de ladingsschattingen sterk ontsporen.

De oude publicatie is [Edukaizen deel 6: 6x6 tensor baseline, IBM diagnostics, and Fire Opal Fez](https://edukaizen.nl/fermi-hubbard-2d-cuprate-series-part-6-6x6-tensor-ibm-fire-opal-status/), gedateerd 4 juli 2026. De gepubliceerde cijfers komen overeen met de oorspronkelijke lokale resultaatbestanden. De nieuwe runs zijn van 4 september 2026.

## Gelijke vergelijkingsbasis

Alle vier vergelijkingsbestanden bevatten exact dezelfde 36 MPS chi32-referentierijen, inclusief sitecoordinaten, observabelen, stap 1 en tijd 0.1. De oude en nieuwe directe IBM-plannen hebben dezelfde configuratie en dezelfde logische hoofdcircuitsamenvatting.

Het gaat om 36 sites, 72 logische qubits, vier gaten, open randen en de stripe-Neel-begintoestand, met verwacht N_up=N_down=16. De werkelijk gebruikte circuitfamilie is `number_preserving_t_only`.

Modelbeperking uit de code: de configuratie noemt U/t=8 en t'/t=-0.25, maar de t-only-circuitfamilie slaat de t'-hopping over. Deze familie gebruikt tweequbit XXPlusYY-hoppingpoorten; de volledige expliciete Jordan-Wigner-route is een andere codebranch. Overeenstemming met MPS valideert hier deze gedeelde vereenvoudigde circuitproef. Dat onderscheid geldt voor zowel de oude als nieuwe resultaten.

## RMSE tegenover dezelfde MPS chi32-referentie

Lager is beter. De eerste drie rijen hebben geen achteraf toegepaste readoutcorrectie of sectorselectie; Fire Opal bevat uiteraard al zijn eigen providerbewerking. ZNE en PEC zijn de onbegrensde gerapporteerde Estimator-puntschattingen.

| route | ladings-RMSE | spin-z-RMSE | doublon-RMSE |
|---|---:|---:|---:|
| Oud: Marrakesh, raw | 0.332687 | 0.733615 | 0.167283 |
| Oud: Fire Opal Fez, raw | 0.127246 | 0.210454 | 0.116802 |
| Nieuw: Phoenix, raw | 0.137371 | 0.215794 | 0.056048 |
| Nieuw: Phoenix, ZNE | 0.137214 | 0.149804 | 0.057279 |
| Nieuw: Phoenix, PEC | 0.482026 | 0.125025 | 0.171049 |

De gepubliceerde oude readout-gecorrigeerde rijen zijn respectievelijk 0.330085 / 0.731364 / 0.166579 (Marrakesh) en 0.127916 / 0.210285 / 0.117542 (Fire Opal Fez). Hun aanwezigheid verandert het algemene vergelijkingsbeeld niet. De readout-gecorrigeerde rij van de eerste Phoenix-run is uitgesloten wegens de eerder vastgestelde mismatch tussen fysieke meetqubits en kalibratiequbits; zie [de bestaande waarschuwing](ibm_phoenix_budgeted_s128_max5s/READOUT_CALIBRATION_WARNING.md).

Herberekende verschillen, op basis van volledige precisie:

- Phoenix raw tegenover oud Marrakesh raw: 58.7% minder ladingsfout, 70.6% minder spin-z-fout en 66.5% minder doublonfout.
- Phoenix ZNE tegenover oud Marrakesh raw: 58.8%, 79.6% en 65.8% minder fout; foutverhoudingen oud/nieuw 2.42, 4.90 en 2.92.
- Phoenix ZNE tegenover oud Fire Opal Fez raw: ladingsfout 7.8% hoger, spin-z-fout 28.8% lager en doublonfout 51.0% lager.
- Phoenix ZNE tegenover Phoenix raw: ladingsfout praktisch gelijk (-0.1%), spin-z-fout 30.6% lager en doublonfout 2.2% hoger.

Dit zijn verschillen tussen de gemeten puntschattingen. Kleine verschillen zijn bij deze shotbudgetten geen aangetoonde statistische rangorde.

## Circuitkosten en meetbudget

| directe IBM-route | hoofdcircuitshots | getranspileerde diepte | tweequbitpoorten | tweequbitdiepte |
|---|---:|---:|---:|---:|
| Oud Marrakesh | 1024 | 759 | 2397 CZ | 317 |
| Nieuw Phoenix raw | 128 | 249 | 777 CZ | 89 |

Phoenix heeft 67.6% minder CZ-poorten, 67.2% minder totale diepte en 71.9% minder tweequbitdiepte. Dit is een aantoonbaar verschil in de opgeslagen circuits. Backend, connectiviteit, kalibratie, layout en softwaremoment verschillen; de meetresultaten isoleren hun individuele bijdragen niet.

De oude Fire Opal-hoofdmeting gebruikte 1024 shots en de twee readoutcircuits elk 4096. Zijn qelib-invoer had 312 CX en diepte 25; dat is een circuit voor providercompilatie en mag niet rechtstreeks worden gelijkgesteld aan de fysiek gerouteerde 777 CZ op Phoenix.

De nieuwe PEC/ZNE-instelling was default_shots=128. ZNE gebruikte ruisfactoren 1,3,5 en lineaire extrapolatie naar nul. PEC voegde ruisleren toe, met max_overhead=2; Runtime rapporteerde 256 shots en vier randomisaties. Daarom betekenen de nominale shotgetallen geen gelijk totaal meetbudget. Het is ook geen gecontroleerde vergelijking waarmee het voordeel van ZNE of van alleen de chip kan worden vastgesteld.

Beide nieuwe mitigatiejobs hebben een opgeslagen harde uitvoeringslimiet van 5 s en elk 3 providergerapporteerde QPU-seconden. De oudere bestanden bevatten hier geen vergelijkbare definitieve QPU-kostenregistratie; een historische prijs- of snelheidsoverwinning is dus niet vastgesteld. Deze vergelijking zelf heeft geen QPU-tijd gebruikt.

## Fysieke betrouwbaarheid

De exacte deeltjesssector bevatte 19/1024 shots op oud Marrakesh (1.86%), 45/1024 op Fire Opal Fez (4.39%) en 7/128 op Phoenix raw (5.47%). Door het kleine aantal van zeven behouden shots is een nauwkeurige Phoenix-sectorvergelijking nog niet mogelijk. De opgeslagen PEC/ZNE Estimator-uitvoer biedt geen bitstrings waarmee zo'n overlevingspercentage kan worden berekend.

PEC geeft een totale lading van 48.580446 terwijl de doelwaarde 32 is. Bij 29 van de 72 spinorbitalen ligt de bezettingsschatting boven 1. De kleinere spin-z-fout compenseert deze inconsistentie niet. Het geleerde totale ruisoverhead is 21.733177, terwijl de ingestelde PEC-overhead begrensd is op 2 en slechts een unieke laag geleerd wordt. Dat maakt dit een sterk beperkte PEC-proef. Hoge variantie en onvolledige ruiscorrectie zijn relevante verklaringen; de precieze oorzaak is in deze vergelijking niet vastgesteld.

De lokale TDHF-fouten tegenover MPS chi32 blijven 0.001003 / 0.001905 / 0.000682: ook de verbeterde hardware blijft voor deze korte proef veel verder van dezelfde referentie. Er is nog geen nieuwe meting van d-wave-paarcorrelaties, geen nieuwe MPS-convergentieladder en geen aangetoond quantumvoordeel.

## Bronnen en controle

Alle paden hieronder zijn relatief aan deze resultatenmap.

- Oude IBM-RMSE en sitewaarden: `observable_comparison_shallow_t_only_steps1_vs_mps_hardware/`.
- Oude Fire Opal-RMSE en sitewaarden: `observable_comparison_shallow_t_only_steps1_vs_mps_qelib_fallback_ibm_fez/`.
- Nieuwe Phoenix raw: `observable_comparison_ibm_phoenix_budgeted_s128_vs_mps/`.
- Nieuwe PEC/ZNE: `observable_comparison_ibm_phoenix_pec_zne_s128_vs_mps/`.
- Oude IBM-job: `d94cogcql68s73c9clg0`; Fire Opal-acties: `2331691` en `2331692`.
- Nieuwe raw-job: `dadgm5dnj4cs73ads6ng`; ZNE: `dadhl2642tqs73atf07g`; PEC: `dadhlnlnj4cs73adtc3g`.
- Bestaand volledig nieuw runoverzicht: [Phoenix mitigatieaudit](ibm_phoenix_budgeted_mitigation_audit.md).
- Modelcontrole: `cuprate_2d_qiskit_circuit.py`, functies `add_number_preserving_hopping_ansatz` en `build_circuit`; MPS gebruikt dezelfde `build_circuit`.
- [Machineleesbare herberekening en invoerhashes](edukaizen_2d_vs_nighthawk_2026-09-04.json).

De RMSE's zijn onafhankelijk van het Python-vergelijkingsscript opnieuw berekend uit de genormaliseerde site-CSV's: sqrt(sum((waarde-reference)^2)/36). Alle vijftien RMSE's komen overeen met de bestaande CSV-tabellen binnen afronding op floating-pointprecisie. De vier MPS-referenties zijn inhoudelijk identiek; elke rij hoort bij stap 1 en tijd 0.1.

