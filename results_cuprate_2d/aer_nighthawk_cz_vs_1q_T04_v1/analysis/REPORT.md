# CZ versus X/SX: resterende gateruis

Zelfde U/t=8, T=0.4, 18-qubitcircuit; acht twirls x 16 ruistrajecten per model.
Alle gates behouden; geen T1/T2, uitleesruis of mitigation in de primaire vergelijking.

| Ruis op | RMSE lading | RMSE spin | RMSE doublon | Spincontrast | 95%-interval spin-RMSE |
|---|---:|---:|---:|---:|---|
| cz_residual_only | 0.09877 | 0.13296 | 0.08039 | 0.81679 | [0.12158, 0.15050] |
| x_sx_residual_only | 0.02191 | 0.04957 | 0.01997 | 0.93318 | [0.03774, 0.06801] |

CZ minus X/SX spin-RMSE: 0.08339; puntgewijs 95%-interval [0.06222, 0.10350].
2000 fixed-twirl bootstrapherhalingen; geen onbekende model- of driftfouten inbegrepen.
Spincontrast is projectie op het ideale spinpatroon, geen fideliteit.
128 trajecten zijn een screeningbudget, geen convergentiecertificaat; geneste 64/128-resultaten zijn bewaard.
Dit vergelijkt totale circuitbijdragen, niet fout per gate. Componentfouten zijn niet optelbaar.
De extra hardwareafwijking wordt hiermee niet automatisch geidentificeerd.

Verificatie: 29 tests; onafhankelijke observabelenfout 6.66e-16.
Nieuwe QPU-seconden: 0. Aer-runtijden: {"cz_residual_only": 128.3531305659999, "x_sx_residual_only": 116.81974787299987}
