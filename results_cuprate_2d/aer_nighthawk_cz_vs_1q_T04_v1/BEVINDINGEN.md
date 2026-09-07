# CZ-restfouten geven het grootste onderzochte gateklasse-effect

De lokale CZ-versus-X/SX-proef is afgerond op hetzelfde meetpunt: 3x3
Hubbard, U/t=8, T=0.4, twee Trotterstappen, 18 actieve qubits en acht twirls.
Per variant zijn 128 nieuwe ruistrajecten gebruikt, met rechtstreeks
opgeslagen Pauli-verwachtingswaarden. Er is geen QPU-budget verbruikt.

**Binnen de resterende depolariserende gateruis van dit Aer-model geeft
CZ-ruis een duidelijk grotere spinfout dan X/SX-ruis.** Beide proeven
bevatten nog steeds ALLE oorspronkelijke gates, inclusief 1008 CZ per
circuit. Alleen de foutkanalen op de gekozen gateklasse zijn ingeschakeld.

| Ruis op | RMSE lading | RMSE spin | 95%-interval spin-RMSE | RMSE doublon | Spincontrast g |
|---|---:|---:|---:|---:|---:|
| Alleen CZ | 0.09877 | 0.13296 | [0.12158, 0.15050] | 0.08039 | 0.81679 |
| Alleen X/SX | 0.02191 | 0.04957 | [0.03774, 0.06801] | 0.01997 | 0.93318 |

De spin-RMSE is tegenover de identieke ideale eindige circuitreferentie,
over negen sites. Spin is n_up-n_down. Spincontrast is de projectie op het
ideale spinpatroon (ideaal=1), geen fideliteit of percentage intacte toestand.

Verschil CZ minus X/SX in spin-RMSE: **0.08339**, met puntgewijs
95%-bootstrapinterval **[0.06222, 0.10350]**. Dat interval is ook rechtstreeks
uit de opgeslagen bootstraptrajecten opnieuw gecontroleerd.
Het verschil in spincontrast is -0.11639, met interval [-0.14591, -0.08520].

## Wat is hiermee getest?

Het gaat specifiek om de eerder afgeleide resterende depolarisatie, niet
om het volledige fysieke CZ-foutbudget. T1/T2-relaxatie en uitleesruis
zijn uitgeschakeld in deze primaire vergelijking. Er zijn geen parameters
op de hardwaredata gefit en er is geen nieuwe kalibratie opgehaald.

De ruiskanalen zijn rechtstreeks uit het vorige opgeslagen model gesplitst.
Hun supports zijn disjunct en vormen samen exact het oorspronkelijke
restmodel. Het grootste verschil tussen de oorspronkelijke en gesplitste
superoperator-elementen is 3.33e-16. De volledige noise-off circuits komen
op alle acht twirls overeen met de exacte referentie tot 2.2649e-14.

Als aanvullende berekening is hetzelfde uitleeskanaal analytisch op de
trajectmomenten toegepast: spin-RMSE 0.14250 voor CZ plus uitlezen en 0.06438
voor X/SX plus uitlezen. Daarvoor zijn geen extra simulaties uitgevoerd.

## Grenzen van deze screening

- 2000 bootstrap-herhalingen binnen de vaste acht twirls; puntgewijze
  intervallen, zonder onbekende modelonzekerheid of drift tussen jobs.
- Bij de eerste 64 versus alle 128 trajecten verandert spin-RMSE van
  0.15748 naar 0.13296 (CZ) en van 0.06534 naar 0.04957 (X/SX). De rangorde
  blijft, maar de absolute waarden verschuiven: geen convergentiecertificaat.
  Deze deelreeksen zijn genest, niet onafhankelijke replicaties.
- De vergelijking betreft totale effecten in dit specifieke circuit,
  niet de kwaliteit per gate. Gatenummers en locaties verschillen per klasse.
- De oude volledige restgate-run had spin-RMSE 0.14806. Dat is een
  onafhankelijk historisch sample met dezelfde 128-trajectestimator.
  Component-RMSEs mogen niet worden opgeteld en zijn geen additieve
  procentuele uitsplitsing van die oude uitkomst of van de hardwarefout.
- Deze test identificeert niet de extra hardwareafwijking. Idle-relaxatie,
  coherente/contextafhankelijke fouten, crosstalk, leakage en drift blijven
  buiten dit eenvoudige model. Er is geen ZNE of PEC toegepast.

## Vervolg en bewaren

Een gerichte volgende gevoeligheidsproef is: het VOLLEDIGE Aer-ruismodel
behouden en alleen de resterende CZ-depolarisatie halveren. Vergelijk dat
met een volledig model met dezelfde trajectestimator en hetzelfde budget.
Zo meten we de mogelijke marginale spinwinst terwijl de overige fouten
aanwezig blijven. Dit is een hypothetische ruisreductie, nog geen gerealiseerde
hardwaremitigation en geen bewijs dat ZNE/PEC die winst daadwerkelijk behaalt.

Aer.run plus resultaat ophalen: **128.35 s voor CZ**, **116.82 s voor X/SX**,
samen **245.17 s = 4.09 minuten** op twee CPU-threads. Exclusief voorbereiding,
ideale controles, tests, opslag en analyse. Nieuwe QPU-seconden: **0**.

De physics-werkwijze heeft gezorgd voor een vooraf vastgelegd protocol,
29 tests, onveranderde gatekanalen, onzekerheidsanalyse en onafhankelijke
nacontrole via tweesitewaarschijnlijkheden. Het grootste verschil met die
onafhankelijke fysieke observabelen is 6.66e-16. Broncode, circuits, alle
trajectmomenten, seeds, ruiskanalen en hashes zijn bewaard. Eerdere hardware-
en Aer-archieven zijn ongewijzigd. Definitieve status: `COMPLETION.json`.
