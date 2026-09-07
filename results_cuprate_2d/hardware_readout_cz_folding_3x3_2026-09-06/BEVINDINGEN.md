# Hardwarepilot voltooid: spin verbetert, ladingprofiel verslechtert

Eén nieuwe job op Nighthawk (`ibm_phoenix`) is succesvol afgerond:
`daem7r642tqs73autong`. Werkelijk verbruik: **3 QPU-seconden**, onder de
vooraf ingestelde en door IBM bevestigde limiet van 5 seconden.
Alle **808 shots** en alle 26 scalaire PUB-resultaten zijn ontvangen.
Er is niet opnieuw ingediend en geen extra hardwarejob gestart.

## Resultaat bij hetzelfde doelcircuit

3 × 3 spinvol Fermi-Hubbard, 18 modes, U/t = 8, T = 0,4, twee Trotterstappen,
t' = -0,25, Nup = Ndown = 4. De referentie is het exacte eindige Trottercircuit,
niet de exacte continue dynamica. Spin betekent nup - ndown, niet Sz.
RMSE hieronder is de fout over de negen afzonderlijke sites; lager is beter.

| Methode | Lading-RMSE | Spin-RMSE | Doublon-RMSE |
|---|---:|---:|---:|
| Raw, 512 shots | 0,13884 | 0,36824 | 0,13723 |
| Alleen readout, 384 + 128 kalibratie | 0,14040 | 0,36699 | 0,13136 |
| Readout + CZ-folding-ZNE, 384 + 128 kalibratie | 0,19216 | 0,26604 | 0,13309 |
| ZNE zonder readout, gepaarde diagnostiek | 0,18829 | 0,27657 | 0,13501 |

De primaire spin-RMSE-afname is **0,10220**, oftewel **27,75%**.
Het hybride 95%-interval voor de absolute afname is [0,03974; 0,14081],
en voor de relatieve afname [10,70%; 38,41%]. Onder de vastgelegde
onzekerheidsanalyse is de spinverbetering dus duidelijk opgelost.
Dezelfde bootstrap met vaste kalibratie geeft [0,04119; 0,14083].

De lading-RMSE neemt daarentegen toe met 0,05332. Het interval voor
raw-minus-mitigated is [-0,11203; -0,02174]: een duidelijke verslechtering
binnen dezelfde statistische analyse. Voor doublonen is de kleine centrale
winst niet opgelost: interval [-0,03433; 0,02756].

## Wat voegt readout-correctie boven op ZNE toe?

Op precies dezelfde ZNE-meetdata gaat spin-RMSE van 0,27657 naar 0,26604,
ongeveer 3,8% lager. De absolute extra winst heeft interval [0,00305; 0,01659].
Voor lading en doublonen is de extra readoutwinst niet duidelijk opgelost.
De zonder-readoutvariant is een gepaarde diagnostiek: de vrijgekomen
kalibratieshots zijn niet achteraf aan nieuwe doelmetingen toegewezen.

Alle drie hoofdarmen hebben 512 shots inclusief hun vereiste kalibratie.
De totale hardware-uitvoering is groter dan één arm, omdat ook verse
raw-controlemetingen worden verzameld. Gedeelde shots zijn correct gekoppeld
in de onzekerheidsberekening; ze zijn niet behandeld als onafhankelijke data.

## Deeltjesgetal is niet hetzelfde als een goed ladingprofiel

De verwachte totale bezetting hoort 8 te zijn:

- raw: 8,59961;
- alleen readout: 8,50491;
- readout + ZNE: 8,12549.

Het totale aantal komt dus dichter bij de juiste waarde, terwijl de verdeling
over de afzonderlijke sites slechter wordt. Alleen de totale lading beoordelen
zou hier een onterecht gunstig beeld geven. De MSE over alle 27 Pauli-momenten
daalt van 0,15976 naar 0,11896, maar vervangt de afzonderlijke guardrails niet.
Alle centrale lokale paarwaarschijnlijkheden blijven niet-negatief en alle
Pauli-momenten blijven binnen [-1,1]. Er is niets geclipt of gepostselecteerd.

## Wat is daadwerkelijk uitgevoerd?

- Eén vaste oorspronkelijke fysieke layout en acht expliciete twirls/maskers.
- CZ-factoren 1, 2 en 3: respectievelijk 1008, 2016 en 3024 CZ per circuit.
- Verse factor-1 controle: 8 × 64 = 512 shots.
- Factor 2: 8 × 7 = 56 shots; factor 3: 8 × 14 = 112 shots.
- Uitleeskalibratie: all-zero en all-one, ieder 64 shots; samen 128.
- Totaal: 512 + 56 + 112 + 128 = 808 hardware-shots.
- De primaire ZNE-arm gebruikt 216/56/112 doelshots en 128 kalibratieshots.
- Lineaire extrapolatiegewichten [4/3, 1/3, -2/3], vooraf vastgelegd.
- Geen PEA, PEC, TFLO, ingebouwde twirling of extra DD toegevoegd.

De uitleescorrectie is de geteste lokale inverse-momentmethode, geen uitvoering
van M3 of TREX. De kalibratie schat onafhankelijke 0→1- en 1→0-fouten met een
Jeffreys-posteriorgemiddelde. Dat voorkomt schijnzekerheid bij nul waargenomen
fouten in slechts 64 kalibratieshots, maar introduceert een expliciete prior.
Voorbereidingsfouten, correlaties en drift kunnen buiten dit model vallen.

Gelijk shotbudget is niet gelijk poort-/tijdbudget. De primaire ZNE-arm gebruikt
669312 CZ-toepassingen tegenover 516096 voor raw; de werkelijk uitgevoerde
unie bevat 967680 CZ-toepassingen. De provider rapporteert ongeveer 0,0245 s
circuituitvoering en 3 s QPU-gebruik. Alleen die laatste waarde is de relevante
gebruiksmeting; lokale timingramingen zijn geen facturatiegarantie.
[IBM-gebruiksdefinitie](https://quantum.cloud.ibm.com/docs/en/guides/estimate-job-run-time)

## Verificatie en grenzen aan de conclusie

Het protocol, de circuits, de analyse en de bronhashes stonden vooraf vast
in controlepunt `a4996ca`. Er zijn 74 geslaagde unit-/regressietests, 26 QPY-
roundtripcontroles en 24 ruisvrije controles met maximaal 2,27e-14 afwijking.
Na uitvoering zijn alle provider-PUBs, bitarrays, shotcounts, circuitmetadata
en fysieke QPY-inputs vergeleken met het bevroren plan. Een onafhankelijke
2×2-matrixinversie en afzonderlijke OLS-fit reproduceren de mitigatie tot
4,44e-16; de observabelen tot 3,33e-16. Alle ruwe gegevens zijn bewaard.

De intervallen combineren 2000 gepaarde fixed-twirl-bootstrapreplicaties met
gedeelde kalibratieposterior-trekkingen. Ze zijn geen frequentistisch
dekkingsbewijs en omvatten geen extrapolatiebias, hardwaredrift, gecorreleerde
uitleesfouten of systematische SPAM-fouten. De 200/1000/2000-quantielcontroles
veranderen de hoofdconclusie niet. De prior en beperkte kalibratie blijven
onderdeel van de onzekerheidsinterpretatie.

Dit is één echt hardwaretijdpunt, geen volledige dynamische tijdreeks en
geen quantum advantage. Readout + CZ-folding-ZNE is hiermee ondersteund als
spinmitigatie in deze kleine pilot, niet als universele observabelencorrectie.
Een volgende run of budgetverhoging is niet automatisch uitgevoerd.
