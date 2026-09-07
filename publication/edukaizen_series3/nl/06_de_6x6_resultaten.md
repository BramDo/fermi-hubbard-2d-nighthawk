---
part: 6
title: "Onze 6x6-resultaten: lading, spin en doublons"
slug: "hubbard-nighthawk-serie-3-06-resultaten"
status: draft
language: nl
---
# Onze 6x6-resultaten: lading, spin en doublons

De laatste gepaarde run laat twee dingen tegelijk zien. Readout plus TFLO
levert een veel duidelijker spinprofiel dan de ruwe data. Maar de compacte
circuitversie geeft in deze proef geen betere lokale overeenkomst met onze
klassieke chi64-referentie dan het origineel.

Het gaat om job daf6foe42tqs73avhoeg op ibm_phoenix, met een geregistreerd
QPU-gebruik van 7 seconden voor de hele job. Beide circuitarmen en hun
training, holdouts en kalibraties zijn daarin opgenomen. Het model is
6x6, N=32, U=8, t'=-0,25 en T=0,4 met twee symmetrische stappen.

## Eerst de waarden, daarna de afwijkingen

N is het totale deeltjesaantal. D is de gemiddelde dubbelbezetting per
site. Spin-RMS is de grootte van het lokale spinprofiel, niet zijn fout.

| Methode | N | D per site | Spin-RMS |
|---|---:|---:|---:|
| Origineel, ruw | 35,463 | 0,24065 | 0,01632 |
| Origineel, readout + TFLO | 31,396 | 0,09013 | 0,65683 |
| Compact, ruw | 35,868 | 0,24854 | 0,01935 |
| Compact, readout + TFLO | 31,231 | 0,07719 | 0,67128 |
| Klassieke chi64-referentie | 32,000 | 0,08790 | 0,70346 |

Vooral het verschil tussen de ruwe en de gecorrigeerde spin springt eruit.
Daar staat tegenover dat de correctie informatie uit U=0-training gebruikt.
We moeten dus testen of de uiteindelijke U=8-schatter betrouwbaar is.

De lokale RMS-afwijkingen gebruiken alle 36 sites en vergelijken iedere
observabele afzonderlijk met dezelfde chi64-referentie:

| Methode | Lading | Spin | Doublons |
|---|---:|---:|---:|
| Origineel, readout + TFLO | 0,08389 | 0,09185 | 0,05080 |
| Compact, readout + TFLO | 0,10930 | 0,12586 | 0,06412 |

Deze getallen zijn geen bekende absolute fouten: chi64 is nog niet
geconvergeerd. Ze laten wel zien wat de huidige vergelijking daadwerkelijk
oplevert. Alleen naar het gemiddelde D kijken zou lokale afwijkingen
verbergen die elkaar in de som kunnen opheffen.

## Waarom we N niet simpelweg door 32 vervangen

De ideale Hamiltoniaan behoudt het deeltjesaantal. We weten dus dat N=32
de modelwaarde is. Die mag als constraint worden vermeld. Maar het zou
misleidend zijn om de gemeten N-cel door 32 te vervangen en vervolgens te
zeggen dat de hardware de lading vrijwel perfect heeft gereproduceerd.

Als we een constraint echt in een estimator willen verwerken, moet die
methode vooraf worden beschreven en moeten de lokale waarden en hun
onzekerheden consequent mee veranderen. Eén getal achteraf repareren is
geen gevalideerde mitigatiemethode.

## Hoe ver mogen we de tabel vertrouwen?

De onafhankelijke U=0-holdouts haalden onze screeningseisen niet. Sommige
gereconstrueerde lokale kansen zijn negatief. We bewaren die uitkomsten
zonder clipping. De bootstrapintervallen beschrijven slechts de gekozen
statistische aannames; ze omvatten niet alle drift, transferbias of klassieke
truncatiefout.

Dit is dus een concrete, reproduceerbare hardwaremijlpaal en een leerzaam
mitigatieresultaat. De volgende wetenschappelijke stap is niet een mooiere
tabel, maar een estimator die ook op onafhankelijke controles standhoudt.

Bron: analysis/summary.json en CONCLUSIE.md onder
results_cuprate_2d/hardware_compact_tflo_2026-09-07_v1, plus de opgeslagen
classical_full_6x6_mps_T04_chi64_v1-referentie.
