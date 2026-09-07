# Volledig Aer-model: CZ-restdepolarisatie halveren

Beide modellen: zelfde 128 ruistrajecten als budget, acht twirls, U/t=8, T=0.4.
T1/T2, X/SX-fouten en uitleeskanalen blijven gelijk. Primaire resultaten INCLUSIEF uitleesruis.

| Model | RMSE lading | RMSE spin | RMSE doublon | Spincontrast | 95%-interval spin-RMSE |
|---|---:|---:|---:|---:|---|
| full_calibrated | 0.07704 | 0.25000 | 0.09477 | 0.61668 | [0.22892, 0.27522] |
| full_cz_residual_half | 0.07029 | 0.20376 | 0.07916 | 0.68944 | [0.18694, 0.22428] |

Spin-RMSE reductie: 0.04624; puntgewijs 95%-interval [0.01625, 0.07715].
Relatieve puntinschatting: 18.5%.
2000 fixed-twirl bootstrap-herhalingen; alle seedbereiken zijn gescheiden; geen onbekende model- of hardwarefouten inbegrepen.
CZ-restdepolarisatie halveert, niet de totale CZ-infideliteit: CZ-relaxatie blijft aanwezig.
Dit is geen ZNE/PEC-experiment en geen gerealiseerde hardwareverbetering.
Het oorspronkelijke model mist nog idle-gap-relaxatie, coherente fouten, crosstalk, leakage en drift.
De oude 512-bitshotcontrole en v1 hadden overlappende seedbereiken; hun onafhankelijke bootstrapintervallen zijn voorlopig ongeldig.
De 64/128-trajectreeksen zijn genest en bewijzen geen algemene convergentie.

Verificatie: 35 tests, onafhankelijke fysieke fout 6.66e-16.
Nieuwe QPU-seconden: 0. Aer-runtijden: {"full_calibrated": 181.32446150299802, "full_cz_residual_half": 194.56824945000153}
