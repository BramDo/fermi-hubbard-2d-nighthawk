# Aer:512 bitshots zonder ZNE versus512 totaal met ZNE

Zelfde3x3-circuit, U/t=8, T=0.4; alle acht twirls en volledige gekalibreerde ruis.

| Methode | Lading-RMSE | Spin-RMSE | Doublon-RMSE | Spincontrast g |
|---|---:|---:|---:|---:|
| raw512 | 0.08444 | 0.24186 | 0.08807 | 0.62726 |
| linear_zne512_PRIMARY | 0.08950 | 0.16502 | 0.09000 | 0.76229 |
| quadratic_zne512_SECONDARY | 0.29535 | 0.23241 | 0.13941 | 0.86637 |

Primaire spin-RMSE-afname 0.07683;95%-interval [0.02748,0.10535].
Relatieve verbetering 31.8%.
Positieve verbetering opgelost binnen de steekproefonzekerheid van dit model.

Raw512 gebruikt8x64; ZNE512 gebruikt8x[37,9,18]=[296,72,144].
De eerste296 factor1-shots zijn gedeeld;728 unieke nieuwe bitshots uitgevoerd.
Bootstrap resamplet gedeelde prefix en raw-only suffix afzonderlijk en behoudt
de correlatie tussen beide armen. Factor1 van ZNE gebruikt niet alle512 raw-shots.
Bitstrings bevatten werkelijke Aer-meet- en uitleesruissampling, niet alleen
conditionele verwachtingswaarden. Alleen de bekende X-maskers zijn teruggedraaid.
Geen postselectie, clipping of analytische readoutmitigatie.
Lineaire gewichten[4/3,1/3,-2/3] en shotverdeling stonden vooraf vast.
Kwadratisch is alleen een gevoeligheidscheck, geen achteraf gekozen hoofdresultaat.
Spincontrast-standaardfout ZNE/raw: 2.28.
Intervallen bevatten steekproefruis, maar niet extrapolatiebias of ontbrekende modelruis.
De geneste256/512-check bewijst geen volledige convergentie of herhaalbaarheid.

Gelijk shotbudget is niet gelijk gate-/tijdbudget:ZNE gebruikt1.703125x zoveelCZ.
CPU-tijden zijn geen QPU-facturatie. Deel37/64 van een gemeten raw-bloktijd
wordt niet als een gemeten ZNE-armruntime gepresenteerd.
Het oude5-seconden-QPU-budget is onaangeraakt; nieuwe QPU-seconden:0.
Nieuwe run+result-tijden: {"1": 769.7632678859991, "2": 128.3119963579993, "3": 241.1077438190041}.
50 tests geslaagd; onafhankelijke observabelefout 0.
Geen Nighthawk-hardwareverbetering of quantum advantage aangetoond.
