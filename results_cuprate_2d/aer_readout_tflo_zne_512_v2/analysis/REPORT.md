# Aer: readout + TFLO versus readout + ZNE

Exploratieve uitbreiding met bestaande U8-data en320 nieuwe Aer-shots. Nieuwe QPU-seconden:0.
Iedere hoofdarm heeft512 shots inclusief benodigde kalibratie/training; CZ-/tijdbudget niet gelijk.

| Methode | Lading-RMSE | Spin-RMSE | Doublon-RMSE |
|---|---:|---:|---:|
| raw512 | 0.08444 | 0.24186 | 0.08807 |
| readout384_plus_cal128 | 0.08702 | 0.22609 | 0.08592 |
| readout_TFLO_PRIMARY | 0.03620 | 0.20508 | 0.05745 |
| readout_ZNE_PRIMARY | 0.08983 | 0.16482 | 0.08704 |
| TFLO_without_readout_DIAGNOSTIC | 0.03622 | 0.20507 | 0.05745 |
| ZNE_without_readout_DIAGNOSTIC | 0.09064 | 0.18322 | 0.08951 |
| classical_FLO | 0.03775 | 0.21556 | 0.07454 |

Primair spin-RMSE(ZNE)-spin-RMSE(TFLO):-0.04026;
95%-hybride onzekerheidsinterval [-0.08407,0.02406]. Positief bevoordeelt TFLO.
Dit interval combineert shot-bootstrap en een Jeffreys-kalibratieposterior; geen gegarandeerd frequentistisch95%-interval.
Readout + TFLO krijgt een nieuwe U0-fit; geen U8-referentiedata in training.
Geen postselectie: deze pilot is niet gelijk aan de eerdere hardware-TFLO-analyse.
Readout-correctie is een lokale inverse-momentmethode, geen M3/TREX.
Bekende-noisematrixresultaten zijn alleen een oracle-diagnose, geen gratis kalibratie.
Een betere centrale waarde is zonder guardrails en onzekerheid geen algemene winnaar.
Modelbias, extrapolatiebias, TFLO-transferbias, hardwaredrift en calibratie-preparatiefout zijn niet afgedekt.
Geen hardwarewinst,5-secondenuitvoerbaarheid of quantum advantage aangetoond.

Bronnen: [TFLO](https://arxiv.org/abs/2102.02120); [measurement mitigation](https://qiskit.github.io/qiskit-addon-mthree/).
