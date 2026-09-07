# Aer is bruikbaar om het spinprobleem deels te isoleren

De componentproef is afgerond op hetzelfde 3x3 Hubbard-meetpunt: U/t=8,
T=0.4, twee Trotterstappen, 18 actieve qubits en acht oorspronkelijke twirls.
Er zijn geen QPU-jobs ingediend en geen hardwareparameters op de data gefit.

**Binnen het gekozen kalibratiegebaseerde Aer-model veroorzaakt de resterende
depolariserende gate-ruis het grootste van de drie afzonderlijk onderzochte
effecten op spincontrast. Gate-tijdrelaxatie draagt ook bij; alleen uitleesruis
geeft een veel kleinere spinfout.** Dit is een diagnose binnen een ruismodel,
niet een bewijs dat dezelfde component de ontbrekende hardwarefout verklaart.

| Afzonderlijk model | Spin-RMSE | Puntgewijs 95%-interval | Spincontrast g |
|---|---:|---:|---:|
| Alleen uitleesruis | 0.01847 | Exact binnen het uitleesmodel | 0.9772 |
| Alleen resterende depolarisatie | 0.14806 | [0.13065, 0.17314] | 0.7759 |
| Alleen T1/T2 tijdens gates | 0.09133 | [0.07629, 0.11326] | 0.8700 |

Spin-RMSE is tegenover dezelfde ideale eindige circuitreferentie en over negen
sites. Spin is n_up-n_down. Spincontrast g is de projectie op het ideale
spinpatroon, met ideaal g=1. Het is geen fideliteit of verliespercentage van
de quantumtoestand. Elk van de twee gatecomponenten gebruikt 128 onafhankelijke
ruistrajecten (16 per twirl); de uitleesrij is exact berekend uit de
onafhankelijke asymmetrische Aer-uitleeskanalen.

Het verschil in spin-RMSE (depolarisatie minus relaxatie) is 0.05673,
met puntgewijs 95%-bootstrapinterval **[0.03099, 0.08630]**.
Dit ondersteunt de rangorde in deze componentproef. Er zijn 2000
bootstrap-herhalingen binnen de vaste acht twirls gebruikt. De intervallen
omvatten geen onbekende modelonzekerheid, kalibratiedrift of tussen-jobvariatie.

## Wat levert extra uitleesruis boven op een component op?

De opgeslagen trajecten laten het uitleeskanaal exact op de verwachtingen
toepassen, zonder nieuwe simulatie. Dat geeft spin-RMSE 0.15891 voor
depolarisatie plus uitlezen en 0.10594 voor relaxatie plus uitlezen.
De onzekerheden zijn gekoppeld aan dezelfde trajecten en staan in de analyse.

Ter context: de eerdere volledige Aer-run had spin-RMSE 0.26756 en
spincontrast 0.5896; hardware had 0.42258 en 0.3551. Die twee rijen gebruiken
512 gemeten bitstrings, dus een ANDERE steekproefgrootte en estimator met
extra meetshotruis. De nieuwe componentproef leest verwachtingswaarden per
ruistraject uit. Dat verwijdert de meetshotruis, niet Monte Carlo-onzekerheid
door het eindige aantal ruistrajecten. Geen matched-precision claim.

Component-RMSEs mogen niet bij elkaar worden opgeteld en de componenten
vormen geen additieve procentuele uitsplitsing. De kanalen werken verspreid
over het hele interagerende circuit en kunnen samen een ander effect geven.

## Waarom deze uitsplitsing een geldige modeltest is

- Native circuit, layout, 1008 CZ-gates en uitlees-X-maskers zijn behouden.
- De oorspronkelijke gatefout wordt niet opnieuw volledig aan depolarisatie
  toegerekend wanneer relaxatie wordt uitgezet. De resterende depolarisatie
  is afgeleid uit DEZELFDE gekalibreerde combinatie als de eerdere volle run.
- De gesplitste gatekanalen reconstrueren de oorspronkelijke volle kanalen
  tot maximaal **1.7764e-15** verschil in superoperator-elementen.
- De nieuwe verwachtingswaarde-estimator reproduceert de ideale referentie
  op alle acht circuits tot maximaal **2.2649e-14**.
- 18 unit tests toetsen onder andere alle uitleesmaskers, asymmetrisch uitlezen,
  afzonderlijke ruistrajecten, de kanaalreconstructie en bootstrapvariantie.
- Een aparte eindcontrole rekent de fysieke observabelen via tweesite-
  waarschijnlijkheden opnieuw uit, onafhankelijk van de Pauli-transformatie.

## Grenzen en gericht vervolg

Deze screening van 128 trajecten per gatecomponent is geen algemeen
convergentiecertificaat. De eerste 64 versus alle 128 trajecten en de
bootstrap-resolutie zijn bewaard in `analysis/results.json`.
Het model bevat nog geen idle-gap-relaxatie, coherente/contextafhankelijke
fouten, crosstalk, leakage, initialisatiefouten of drift.

Een gericht vervolg binnen dit model is de resterende gate-ruis verder
splitsen in CZ versus X/SX. Dat toetst of de tweequbitgates de grootste
onderzochte bijdrage leveren. Om de EXTRA hardwareafwijking te begrijpen
blijft daarnaast een aparte idle-aware gevoeligheidsproef nodig; niet aannemen
dat de hier gevonden rangorde die ontbrekende hardwarefout al identificeert.
Er is nog geen TFLO, PEC of ZNE gekozen of toegepast op basis van deze proef.

Aer-rekentijd (run + resultaat ophalen): depolarisatie **106.35 s**,
relaxatie **197.53 s**, samen **303.88 s = 5.06 minuten**, op twee CPU-threads.
Exclusief voorbereiding, ideale controles, tests, opslag en analyse.
Nieuw QPU-verbruik: **0 seconden**. Alle trajectmomenten, masks, seeds,
ruiskanalen, broncodes, onzekerheidsresultaten en eerdere data zijn bewaard.

De physics-werkwijze heeft hier vooral de zuivere kanaalsplitsing, vooraf
vastgelegde vergelijking en scheiding van steekproef- en modelonzekerheid
afgedwongen. De definitieve controle staat in `COMPLETION.json`.

Methode: [Aer save_expectation_value](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.library.save_expectation_value.html).
