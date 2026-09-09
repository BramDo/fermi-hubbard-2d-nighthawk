# Twirl1 centraal Z_up: lokale stabiliteitstest geslaagd

De eerste afzonderlijke operatorberekening voor twirl1 is uitgevoerd en
onafhankelijk gecontroleerd. Alle vooraf vastgelegde chi64/chi128-grenzen
slagen, zowel met de ruwe Gram-matrix als met de exacte ideale norm F00=1.
Er zijn acht NIEUWE operatorstaten berekend; geen twirl0-staat is hergebruikt.

Dit is een numerieke stabiliteitscontrole binnen het bestaande ruismodel,
GEEN bewijs van betere hardwarewaarden, volledige 3x3-validatie of 6x6-go.

## Uitkomst

| Controle chi64 naar chi128 | Uitkomst | Vooraf vastgelegde grens | Status |
|---|---:|---:|---|
| Ruwe volledige Gram-matrix, relatieve verandering | 0.367421% | 1% | geslaagd |
| Volledige Gram-matrix met exact F00=1 | 0.085839% | 1% | geslaagd |
| Noisy/noisy blok G | 0.040168% | 1% | geslaagd |
| Ideaal/noisy overlapvector b | 0.158401% | 1% | geslaagd |
| L1-verandering shot-aware coefficienten | 0.00718143 | 0.05 | geslaagd |

De ruwe ideale operatornorm stijgt van 0.9952492892 naar 0.9996379736.
Het analytische resultaat is exact1 omdat A=U-dagger Z U en Z-squared=I.
Alleen F00 wordt in een APARTE matrixkopie vervangen; G, b en de gewichten
veranderen hierdoor niet. De ruwe waarden blijven opgeslagen.

De gewichten zijn bepaald met de ongewijzigde shot-aware regel eta=1,
N=(43,7,14), zonder targetdata of referentiewaarden:

| Niveau | factor1 | factor2 | factor3 |
|---|---:|---:|---:|
| chi64 | 1.8080302402 | -0.1359330067 | -0.6720972335 |
| chi128 | 1.8116209570 | -0.1371038471 | -0.6745171099 |

Som coefficienten is1. Negatieve gewichten zijn niet afgeknipt. De
voorwaardelijke samplingvariantiegrens bij chi128 is0.1150202; de
operatorprojectiefout in de surrogate objective is0.2018004. Geen van deze
getallen is een gecertificeerde foutgrens voor de hardware-observable.

## Exacte scope en kosten

- Archiefjob daem7r642tqs73autong, backend ibm_phoenix.
- 3x3 spinvol Hubbard,18 actieve modi,N8,U8,T0.4,twee symmetrische circuitstappen.
- Twirl1, centrale Z_up: logisch mode8, fysiek qubit109.
- Providerrecords25/19/2, CZ-factoren1/2/3, met1008/2016/3024 CZ-gates.
- Ideale factor1-arm plus drie noisy armen; onafhankelijk bij chi64 en chi128.
- Ongewijzigde mixed-canonical MPS-kernel en bevroren lokale depolarisatiemodel.
- Centrale readout-kalibratie overgenomen uit de eerder geverifieerde frozen-rule
  artifact; target-bitstrings en exacte targetverwachtingen niet gelezen/gebruikt.
- Rekenprocedure:50.023 s; onafhankelijke audit:3.657 s. Beide exclusief
  interpreter/importopstart, geen claim van geisoleerde hardwarebenchmark.
- Harde proceslimiet600s en blokgrenscontrole590s; geen timeout of herstart.
- Gemeten piek-RSS404,275,200bytes (ongeveer386MiB).
- Acht NPZ-staten, elk kleiner dan10MB; alle arrays, bronhashes en ruwe Grams bewaard.
- Nieuwe QPU-tijd:0. Geen nieuwe metingen, publicatie of push.

## Verificatie

63 tests geslaagd. De onafhankelijke controle heeft alle20 unieke
Gram-overlaps opnieuw gecontracteerd, met omgekeerde tensorvolgorde en een
andere contractieboom. De twee fits zijn opnieuw opgelost als KKT-stelsel.
Maximale overlapafwijking6.66e-16; maximale coefficientafwijking4.88e-15.
Verder20,205 native gates,62 unieke unitaire matrices, masks, fysieke
meetmapping en bron-/input-/outputhashes gecontroleerd.

Zie [uitvoer en grenzen](VERIFICATION.md) en de volledige numerieke
resultaten in chi64.json, chi128.json en summary.json.

## Wat nu?

[Volgende begrensde kandidaat](NEXT_ZDOWN.md): dezelfde controle voor het
centrale Z_down van twirl1. Daarna pas de onsite ZZ-operator. Pas wanneer alle
drie passende operatorberekeningen bestaan, kan een complete vergelijking van
centrale lading, spin en doublons met deze twirl worden uitgevoerd.

Z_down/ZZ zijn in DEZE stap niet berekend. De eerdere onfysische doublonwaarde,
heuristische onzekerheidsintervallen en onbesliste hardwareverbetering blijven
ongewijzigd. De physics-verificatieskill bewaakt expliciet dit onderscheid:
een stabiele modelberekening is nog geen nauwkeurige hardware-uitkomst.
