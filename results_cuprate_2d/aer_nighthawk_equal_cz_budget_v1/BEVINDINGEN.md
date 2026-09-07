# ZNE bij gelijk CZ-budget: verkennende heranalyse

Dit hergebruikt de eerder bekeken bitshots. Het is geen nieuwe, onafhankelijke proef.
De shotverdeling is op de kostenformule gekozen, niet op de prestaties van subsets.

| Grootheid | Zonder ZNE: 512 shots | Lineaire ZNE: 344 shots |
|---|---:|---:|
| Lading-RMSE | 0.08444 | 0.11480 |
| Spin-RMSE | 0.24186 | 0.16194 |
| Doublon-RMSE | 0.08807 | 0.10816 |
| Spincontrast g | 0.62726 | 0.77047 |

Spin-RMSE-afname: 0.07992; voorwaardelijk 95%-interval [0.01557, 0.11343].
Relatieve puntinschatting: 33.0% minder spinfout;
interval [6.4%, 46.7%].
Het interval ligt boven nul binnen deze vaste subset- en modelanalyse.
Deze intervallen zijn niet gecorrigeerd voor eerdere analyses en zijn geen bevestiging
door een onafhankelijke herhaling. Extrapolatiebias en modelonzekerheid ontbreken.

## Kosten en selectie

Beide armen: exact 516.096 CZ-applicaties, ook gelijk per fysieke geordende koppeling.
ZNE gebruikt factoren 1/2/3 met respectievelijk 240/40/64 shots: totaal 344.
De eerste 240 factor-1-shots zijn gedeeld met raw512; die correlatie zit in de bootstrap.
De unieke geselecteerde deelverzameling bevat 616 bestaande bitstrings.
De overige 112 parent-bitstrings blijven ongewijzigd bewaard.
ZNE heeft 43/64 van de eenqubitgate- en meetcounts van raw512.
Gelijk CZ-budget is niet bewezen gelijke wandklok- of gefactureerde QPU-tijd.
Aan deze heranalyse wordt geen deel van oude simulatietijden als nieuwe meting toegekend.
Nieuwe shots: 0. Nieuwe QPU-seconden: 0.

## Controles en beperkingen

19 deterministische tests geslaagd; geen quantumcircuit uitgevoerd.
Onafhankelijke bit-naar-observabelefout 0; armreconstructiefout 8.88e-16.
Alle parent-hashes, ruwe hexdata, tellingen, maskers en selectie-indices gecontroleerd.
De lineaire extrapolatie en de primaire foutmarge zijn onafhankelijk nagerekend.
Spincontrast-standaardfout ZNE/raw: 2.78.
Negatieve lokale kansen in primaire puntschatting: 0; geen clipping.
Kwadratisch geeft spin-RMSE 0.46270 en blijft alleen een gevoeligheidscheck.
De halve-budgetsubset is geen onafhankelijke herhaling of convergentieverklaring.
Dit is dezelfde 3x3, 18-mode Hubbard-instantie, U/t=8, T=0.4, twee Trotterstappen.
De referentie is het ideale eindige circuit; geen extra claim over Trotterfout.
Spin is n_up-n_down=2*S_z. g is geen fidelity.
Het approximate Aer-model mist onder meer idle-gap-ruis, coherente/contextuele fouten,
crosstalk, leakage, preparatiefouten en drift. Geen hardware- of quantum-advantagebewijs.
Protocol, broncode, volledige foutmarges en exacte selectie zijn in dit archief bewaard.
