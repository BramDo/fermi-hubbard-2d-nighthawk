# Twirl1 centraal Z_down: lokale stabiliteitstest geslaagd

Ook de tweede centrale operator van twirl1 doorstaat de vooraf vastgelegde
chi64/chi128-controle. Alle acht operatorstaten zijn afzonderlijk berekend;
Z_up- en twirl0-staten zijn niet hergebruikt. De onafhankelijke audit slaagt.

Dit brengt ons op twee van de drie centrale operatoren voor twirl1. Het is
numerieke stabiliteit binnen een bevroren ruismodel, GEEN bewezen hardware-
nauwkeurigheid. De onsite ZZ-berekening en de hardwarevergelijking ontbreken nog.

## Numerieke resultaten

| Controle chi64 naar chi128 | Verandering | Grens | Status |
|---|---:|---:|---|
| Ruwe volledige Gram-matrix | 0.297135% | 1% | geslaagd |
| Volledige Gram-matrix met exact F00=1 | 0.078576% | 1% | geslaagd |
| Noisy/noisy blok G | 0.023303% | 1% | geslaagd |
| Ideaal/noisy overlapvector b | 0.120175% | 1% | geslaagd |
| L1-verandering shot-aware gewichten | 0.00834277 | 0.05 | geslaagd |

De ruwe ideale norm stijgt van0.9951771818 naar0.9996343587.
De exacte norm van U-dagger Z_down U is1. Alleen F00 wordt in een aparte
matrixkopie vervangen; alle ruwe waarden blijven bewaard. De gewichten zijn
bit-identiek voor en na deze normcorrectie.

| Niveau | factor1 | factor2 | factor3 |
|---|---:|---:|---:|
| chi64 | 1.5892570472 | -0.0937735826 | -0.4954834647 |
| chi128 | 1.5934284297 | -0.0950813350 | -0.4983470948 |

Som(c)=1. De ongewijzigde shot-aware regel gebruikt eta1,N=(43,7,14).
De readoutbijdrage komt expliciet van de TWEEDE centrale modus, niet van
Z_up. De huidige twee kalibratiemodi geven toevallig dezelfde penaltywaarden;
vier nieuwe tests met bewust verschillende kalibraties controleren de selectie.

Bij chi128: surrogate operatorprojectiefout0.1475862953,
voorwaardelijke samplingvariantiegrens0.0805365958, som0.2281228911.
Dit zijn geen gecertificeerde hardware-MSE- of observablefoutgrenzen.
Negatieve coefficienten worden niet afgeknipt.

## Scope en budget

- Bestaande job daem7r642tqs73autong, backend ibm_phoenix.
- 3x3 spinvol Hubbard,18 actieve modi,N8,U8,T0.4,twee symmetrische circuitstappen.
- Twirl1, centrale mode9 Z_down, fysiek qubit108.
- Native providerrecords25/19/2; CZ-factoren1/2/3:1008/2016/3024 CZ.
- Ideale factor1-arm plus drie noisy armen bij chi64 en chi128.
- Ongewijzigde canonical-MPS-propagatie, lokale depolariserende surrogate,
  readout-kalibratie, shot-aware regel en acceptatiegrenzen.
- Rekenprocedure54.351s; onafhankelijke audit3.623s, exclusief importopstart.
- Hard600s procesbudget, klokcontrole tussen blokken na590s; geen timeout/herstart.
- Piek-RSS397,201,408bytes, ongeveer379MiB.
- Acht NPZ-bestanden, elk kleiner dan10MB; alle numerieke staten bewaard.
- Geen nieuwe QPU-tijd, target-scoring, publicatie of push.

## Verificatie en betekenis

67 tests geslaagd. Onafhankelijke herberekening van20 Gram-overlaps via ruwe
tensor-netwerken en een andere contractievolgorde; twee directe KKT-oplossingen.
Maximale overlapafwijking1.11e-15; maximale coefficientafwijking7.27e-15.
Verder20,205 native gates,62 unieke unitaire matrices, meetmapping, maskers,
de tweede kalibratiemodus en alle bron-/input-/outputhashes gecontroleerd.

| Twirl1 centrale operator | Gecontroleerde niveaus | Exact-norm F-verandering | Lokale status |
|---|---|---:|---|
| Z_up | chi64/128 | 0.085839% | geslaagd in vorige stap |
| Z_down | chi64/128 | 0.078576% | geslaagd in deze stap |
| Z_up Z_down | nog niet berekend | niet beschikbaar | volgende kandidaat |

De physics-verificatieskill heeft de onafhankelijke modeselectiecontrole en
het onderscheid tussen modelstabiliteit en hardwarevalidatie bepaald.
Geen hardwarewaarden zijn gewijzigd. De eerdere negatieve doublons en
onbesliste verbeteringsintervallen blijven dus staan.

Volgende stap: [een eigen, begrensde ZZ-controle](NEXT_ZZ.md). Eerst daarna
de complete centrale lading/spin/doublonvergelijking op de opgeslagen twirl1-
hardwaredata. Nog geen groen licht voor6x6.
