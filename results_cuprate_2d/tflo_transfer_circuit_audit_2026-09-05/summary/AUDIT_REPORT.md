# Lokale TFLO-overdrachtaudit, circuitroutes en Trotterfout

**0 nieuwe QPU-seconden. Alle oorspronkelijke resultaten en indieningslocks zijn behouden.**

## 1. TFLO-overdracht op bestaande data

Alle modellen zijn uitsluitend met zes U=0-punten getraind. De twee U=0-validatiepunten en alle U=8-punten bleven buiten de fit. De audit is post-hoc/verkennend: geen methode wordt tot nieuwe primaire uitkomst gepromoveerd.

| Model | U=0 validatie-MSE | U=8 MSE | Interactiecontrast-MSE | Projectie op exact interactiecontrast |
|---|---:|---:|---:|---:|
| linear_linear | 0.002336 | 0.033645 | 0.034419 | 0.0279 |
| affine_no_time | 0.059559 | 0.074497 | 0.088715 | 0.1305 |
| time_only | 0.002344 | 0.031355 | 0.033533 | 0.0000 |

Exacte klassieke U=0-FLO-voorspelling op U=8-doelen: MSE 0.033533.
De projectie is een beschrijvende schaalfactor van het voorspelde verschil U=8 minus U=0 langs het exacte verschil. Een factor 1 alleen bewijst geen juiste observabelen; orthogonale fouten tellen in de contrast-MSE mee. De U=0-contrastpartners zijn trainingspunten, niet nieuwe holdouts.

- linear_linear: 95%-interval winst boven klassieke FLO {'low': -0.006025630182634451, 'high': 0.00474996381339373, 'valid': 400}; contrastprojectie {'low': -0.05111029384808303, 'high': 0.1018638322495605, 'valid': 400}.
- affine_no_time: 95%-interval winst boven klassieke FLO {'low': -0.08436677114576054, 'high': 0.0006309090520616641, 'valid': 400}; contrastprojectie {'low': -0.1853596510562855, 'high': 0.5382087039284142, 'valid': 400}.
- time_only: 95%-interval winst boven klassieke FLO {'low': 0.0021785774475671163, 'high': 0.0021785774475671163, 'valid': 400}; contrastprojectie {'low': 0.0, 'high': 0.0, 'valid': 400}.

Ablatie huidige TFLO: echte U=8-input MSE 0.033645; vervangen door U=0-input 0.033037.
95%-interval voor de winst van de echte U=8-input: {'low': -0.007416363732061995, 'high': 0.003803831320515626, 'valid': 400}.
Bootstrap: 400 aangevraagd, 0 mislukte resamples. Intervallen sluiten transferbias en drift uit.

## 2. Exact dezelfde ideale circuitwerking, andere routing

| Route | CZ | Twee-qubitdiepte | Totale diepte | Circuitduur uit opgeslagen kalibratie |
|---|---:|---:|---:|---:|
| network | 1008 | 144 | 549 | 18.772 us |
| left | 1412 | 420 | 1126 | 43.820 us |
| right | 1624 | 532 | 1578 | 57.916 us |
| look4 | 1040 | 396 | 1062 | 41.148 us |
| look12 | 1032 | 428 | 1122 | 43.964 us |

Minimum-CZ-kandidaat: network; CZ-reductie 0.00%.
De volgorde van niet-commuterende Hamiltoniantermen is behouden. Fermiontekens en modevolgorde zijn gecontroleerd. Zeven basistests bevatten volledige 2x2-operatorvergelijkingen; alle kandidaten zijn daarnaast op drie volledige 18-qubitdoeltoestanden getest.
Acht getwirlde fysieke templates van de minimum-CZ-kandidaat zijn opnieuw gevalideerd, met hun eigen readoutmaskers. De 80 parameterbindings en QPY-herlaadtests zijn gecontroleerd. Dit is geen nieuwe hardwaremeting of submissietoestemming.
Kalibratiebron: 2026-09-05T17:38:21.910870+00:00; alle 5120 shots met reset/rep_delay samen lokaal geraamd op 0.114237 s, exclusief provideroverhead.
Minder CZ kan samengaan met grotere diepte. Een lokale gatebesparing bewijst geen hardwarefidelitywinst.

## 3. Exacte continue Hubbard-dynamica versus eindige Trotterstappen

| U/t | Tijd | Stappen | Lading RMSE | Spin RMSE | Doublon RMSE |
|---|---:|---:|---:|---:|---:|
| 0 | 0.2 | 2 | 0.000573 | 0.000270 | 0.000272 |
| 0 | 0.2 | 4 | 0.000144 | 0.000068 | 0.000068 |
| 0 | 0.2 | 8 | 0.000036 | 0.000017 | 0.000017 |
| 0 | 0.4 | 2 | 0.006369 | 0.001667 | 0.002895 |
| 0 | 0.4 | 4 | 0.001618 | 0.000416 | 0.000733 |
| 0 | 0.4 | 8 | 0.000406 | 0.000104 | 0.000184 |
| 8 | 0.2 | 2 | 0.001099 | 0.005835 | 0.002775 |
| 8 | 0.2 | 4 | 0.000266 | 0.001420 | 0.000685 |
| 8 | 0.2 | 8 | 0.000066 | 0.000353 | 0.000171 |
| 8 | 0.4 | 2 | 0.004809 | 0.038274 | 0.019002 |
| 8 | 0.4 | 4 | 0.001036 | 0.008356 | 0.004348 |
| 8 | 0.4 | 8 | 0.000252 | 0.002020 | 0.001063 |

U=8,T=0.2: toestandsfout-ratio's 2/4 en 4/8 stappen: [4.064707614301242, 4.016137157973089].
De bestaande hardware-TFLO-observabelen rechtstreeks tegenover exacte H-dynamica: RMSE lading/spin/doublon [0.029604192451791078, 0.09239530585242274, 0.02840624846802622].

U=8,T=0.4: toestandsfout-ratio's 2/4 en 4/8 stappen: [4.2819002353626665, 4.06999871049609].
De bestaande hardware-TFLO-observabelen rechtstreeks tegenover exacte H-dynamica: RMSE lading/spin/doublon [0.0564359900932413, 0.24216295525057097, 0.09113246271735026].

Trotterbias en meet-/mitigatiefout zijn aparte foutbronnen. De directe vergelijking met exacte H hierboven telt ze niet ten onrechte als onafhankelijke statistische fouten op.
32 numerieke Hamiltonian-, norm-, sector-, FLO- en referentiecontroles geslaagd.

## Grenzen en vervolg

Geen nieuwe fit op U=8, geen gunstige sites geselecteerd, geen extra PEC/ZNE, geen negatieve waarden geclipt. Een eventueel kansrijk alternatief moet op nieuwe, vooraf vastgelegde meetdata worden bevestigd. Deze audit is geen quantum-advantagebewijs en wijzigt geen eerder resultaat.
[2D-paper: TFLO-overdracht, controles en circuitkosten](https://arxiv.org/html/2510.26845v2).

Eindcontrole: 14 aanvullende controles; alle regressietests geslaagd (zie unit_tests.txt).
