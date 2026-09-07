# 6x6: mitigatie toegepast waar bestaande shots dat toelaten

**Extra sectorselectie helpt hier niet aantoonbaar om het spinprofiel te
herstellen. TFLO en dynamische ontkoppeling zijn nog NIET uitgevoerd.**
Er is geen nieuwe hardwarejob gestart: 0 extra QPU-seconden.

| Arm | N | RMS-afstand lading | RMS-afstand spin | RMS-afstand doublons |
|---|---:|---:|---:|---:|
| Ruw | 35.769 | 0.279 | 0.704 | 0.165 |
| Bestaande readout + CZ-ZNE | 35.768 | 0.279 | 0.703 | 0.165 |
| Nieuw: strikte sectorselectie | 32.000 | 0.265 | 0.715 | 0.131 |
| Nieuw: ZNE + sector-ratio, diagnostisch | 32.000 | 0.288 | 0.726 | 0.143 |

Alle RMS-afstanden zijn tegenover de opgeslagen klassieke chi=64-berekening
van hetzelfde eindige circuit, niet tegenover een exact gecertificeerd antwoord.
Spin betekent n_up-n_down, niet S_z. De nieuwe sectorarmen bevatten GEEN
readout-inversie; de oorspronkelijke readout+ZNE-arm blijft apart staan.

## Wat de extra mitigatie wel en niet doet

- Strikte selectie op N_up=N_down=16 behoudt slechts 48/4096 shots bij
  factor 1 (1.17%). Factoren 2 en 3 behouden 46 en 45 shots.
- N=32 is daarna afgedwongen, geen onafhankelijke validatie.
- De RMS-afstand voor doublons wordt 0.0340 kleiner. Een gepaarde,
  voorwaardelijke bootstrap geeft voor de vermindering een 95%-interval
  van 0.0041 tot 0.0394. Dit is geen gecertificeerde hardwarefoutreductie:
  referentiefout en selectiebias zitten niet in dit interval.
- Voor spin is de vermindering -0.0113 (puntwaarde slechter), met interval
  -0.0473 tot +0.0110. Geen aantoonbare positieve verbetering.
- De ZNE+sector-ratio geeft bovendien een negatieve lokale kans, minimaal
  -0.0473. De schatting is niet geclipt; deze arm is geen fysische
  gereconstrueerde toestand en geen geaccepteerde verbetering.

2000 whole-shot bootstrapreplica's met vaste twirls; baseline-readoutarmen
nemen ook onzekerheid in onafhankelijke uitleeskanalen mee. Geen totale
foutgrenzen: drift, gecorreleerde SPAM, selectie-/extrapolatiebias, MPS-
truncatie en Trotterfout ontbreken. De shotbudgetten zijn niet gelijk.

## Volledige gevraagde mitigatie: nog geblokkeerd op nieuwe hardwaredata

De beschikbare TFLO-training betreft 3x3, de recente U=0-controle 5x5.
Geen van beide kan als een gevalideerde 6x6-training worden overgenomen.
DD voegt tijdens uitvoering pulsen toe en kan niet op oude bitstrings
worden toegepast. Deze offline vergelijking is dus slechts een gedeeltelijke
uitvoering van de gevraagde sterkere mitigatie, niet een TFLO/DD-resultaat.

Voorstel voor de volgende, afzonderlijk te autoriseren pilot:

1. Zelfde volledige 6x6-doel, layout en native gatestructuur, met readout
   en handmatige CZ-/readout-twirling; DD uit/aan als gematchte armen.
2. Per arm zes U=0-trainingsinstellingen, twee afzonderlijke U=0-holdouts
   en het U=8-doel bij T=0.4. Compileer voor parameterbinding, met twee
   vaste stappen. Training nooit op U=8 of MPS-antwoorden.
3. Controleer holdouts en vergelijk ook met een puur klassieke U=0-
   voorspelling en een fit met weggelaten hardware-input. Alleen beter
   dan raw worden is onvoldoende om nuttige kwantuminformatie aan te tonen.
4. Vers budget- en ISA-onderzoek voor indienen; voorgestelde cap 15
   QPU-seconden, uitsluitend na nieuwe toestemming. Dit is geen raming,
   garantie van voltooiing, beschikbare quota of reeds ingestelde limiet.
   Geen automatische retry en geen hergebruik van oude autorisatie.

De [Google/Phasecraft-paper](https://arxiv.org/html/2510.26845v2) motiveert
TFLO, sectorselectie en aanvullende ruisonderdrukking; de daar gevonden
prestatie is geen garantie voor onze circuits.

## Verificatie en bewaring

Acht unit-tests geslaagd; 97 bronarchiefhashes gecontroleerd. Onafhankelijke
integer-decoding en directe site-observabelen geven exact dezelfde selectie
en profielen. Een aparte least-squaresberekening reproduceert de ZNE-ratio
tot 8.9e-16. Alle oorspronkelijke brondata zijn ongewijzigd.

De physics-skill bepaalde de scheiding tussen afgedwongen deeltjesbehoud
en gemeten spinherstel, plus de onafhankelijke controles. Zie summary.json,
verification.json, independent_verification.json, bootstrap.npz en de
broncodekopieën. Geen quantum advantage aangetoond.
