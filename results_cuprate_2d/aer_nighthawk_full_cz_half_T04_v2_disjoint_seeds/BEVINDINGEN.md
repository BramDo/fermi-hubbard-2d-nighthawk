# Gecorrigeerde Aer-test: halvering van CZ-restdepolarisatie

Primaire vergelijking met gescheiden seedbereiken: hetzelfde 3x3 spinvolle
Hubbard-circuit, U/t=8, T=0.4, twee Trotterstappen, 1008 CZ per twirl.
128 ruistrajecten per model; alle acht twirls behouden. Referentie is
het ideale eindige Trottercircuit, niet een extra claim over Trotterconvergentie.

| Grootheid | Volledig model | Alleen CZ-restdepolarisatie half |
|---|---:|---:|
| Lading-RMSE | 0.07704 | 0.07029 |
| Spin-RMSE | 0.25000 | 0.20376 |
| Doublon-RMSE | 0.09477 | 0.07916 |
| Spincontrast g | 0.61668 | 0.68944 |

Spin-RMSE neemt af met 0.04624; puntgewijs 95%-interval
[0.01625, 0.07715]. Relatieve afname 18.5%,
interval [6.9%, 28.3%].
Spincontrast neemt toe met 0.07276; interval [0.02718, 0.11950].
Spin is n_up-n_down; g is projectie op het ideale spinprofiel, geen fidelity.
Intervallen: 2000 fixed-twirl bootstraps van volledige trajectvectoren;
alleen Monte-Carlo-onzekerheid binnen dit model, geen hardware/modelonzekerheid.

## Wat is wel en niet aangetoond

De spinverbetering is in deze lokale modelscreen statistisch opgelost.
Alle overige gemodelleerde fouten, inclusief CZ-T1/T2 en uitleesruis, zijn gelijk.
De totale CZ-infideliteit halveert dus niet. Uitleesruis is eenmaal analytisch
toegepast op premeasurement-expectaties; dit zijn geen hardware-bitshots.
Lading/doublon-verbetering beoordelen op hun eigen intervallen in analysis/results.json.
Dit is een hypothetische kanaalreductie, geen uitgevoerde ZNE of PEC,
geen gemeten hardwareverbetering en geen bewijs van quantum advantage.
Het model mist onder meer idle-gap-relaxatie, coherente/contextuele fouten,
crosstalk, leakage, preparatiefouten en drift. Nighthawk voorspellen vereist
nog een gecontroleerde koppeling aan hardwareobservabelen en modelvalidatie.

## Verplichte correctie van eerdere onzekerheid

In v1 en eerdere Aer-screens overlapten de runseeds over de shot-index.
Dat is bevestigd in de vastgelegde Aer 0.17.2-bron en met een goedkope test.
De eerdere bootstrapintervallen en daarop gebaseerde significantieclaims
zijn daarom voorlopig; de originele data en puntwaarden zijn niet veranderd.
V1: spin-RMSE 0.20802 -> 0.16801 (19.2%). Gebruik die oorspronkelijke
foutmarges niet als bewijs; deze v2-herhaling is nu primair.
De oudere 512-bitshotcontrole had g=0.58959, v1 had g=0.68522.
De seed-cluster-schatting maakt hun standaardfouten circa 1.8x en 2.1x
groter. Dat verklaart niet bewezen de hele controleafwijking. De afwijking
wordt niet weggepoetst door naar een andere estimator te verwijzen.
Zie AER_SEED_CORRECTION_2026-09-06.md en het afzonderlijke impact-archief.

## Verificatie en kosten

35 tests geslaagd.
Alle 256 shot-seedlabels verschillend; geordende native gate-sporen op iedere
wire identiek tussen oude controle, v1 en v2 voor alle acht twirls.
Onafhankelijke reconstructiefout observabelen: 6.66e-16.
Volledig controlemodeI gelijk aan opgeslagen oorspronkelijke quantumkanalen
tot 3.56e-15; readout op alle 18 modes identiek; noise-off maxfout 2.27e-14.
Aer run+result samen 375.89 s (6.26 min) voor v2.
Dit sluit opzet, preflight, tests, analyse en archiveren uit; geen end-to-end benchmark.
Nieuwe QPU-seconden: 0. Oude hardwarejob en submit-lock niet veranderd.
