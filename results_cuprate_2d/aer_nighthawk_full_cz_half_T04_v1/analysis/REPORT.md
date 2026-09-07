# Volledig Aer-model: CZ-restdepolarisatie halveren

Beide modellen: zelfde 128 ruistrajecten als budget, acht twirls, U/t=8, T=0.4.
T1/T2, X/SX-fouten en uitleeskanalen blijven gelijk. Primaire resultaten INCLUSIEF uitleesruis.

| Model | RMSE lading | RMSE spin | RMSE doublon | Spincontrast | 95%-interval spin-RMSE |
|---|---:|---:|---:|---:|---|
| full_calibrated | 0.07858 | 0.20802 | 0.08598 | 0.68522 | [0.19290, 0.22537] |
| full_cz_residual_half | 0.07002 | 0.16801 | 0.08337 | 0.74455 | [0.15502, 0.18541] |

Spin-RMSE reductie: 0.04001; puntgewijs 95%-interval [0.01763, 0.06193].
Relatieve puntinschatting: 19.2%.
2000 fixed-twirl bootstrap-herhalingen; geen onbekende model- of hardwarefouten inbegrepen.
CZ-restdepolarisatie halveert, niet de totale CZ-infideliteit: CZ-relaxatie blijft aanwezig.
Dit is geen ZNE/PEC-experiment en geen gerealiseerde hardwareverbetering.
Het oorspronkelijke model mist nog idle-gap-relaxatie, coherente fouten, crosstalk, leakage en drift.
De 64/128-trajectreeksen zijn genest en bewijzen geen algemene convergentie.

Verificatie: 30 tests, onafhankelijke fysieke fout 6.66e-16.
Nieuwe QPU-seconden: 0. Aer-runtijden: {"full_calibrated": 200.4158014479999, "full_cz_residual_half": 207.55193906600016}
