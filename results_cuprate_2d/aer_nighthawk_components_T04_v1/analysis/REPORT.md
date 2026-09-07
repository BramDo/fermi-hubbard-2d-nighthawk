# Componenten van het Nighthawk-Aer-ruismodel

Zelfde U/t=8, T=0.4, 18-qubitcircuit en acht twirls. Geen nieuwe QPU-seconden.
Per component 128 ruistrajecten met rechtstreeks opgeslagen Pauli-verwachtingswaarden.
Dit verwijdert meetshotruis, niet onzekerheid door het aantal ruistrajecten.

| Model | RMSE lading | RMSE spin | RMSE doublon | Spincontrast g |
|---|---:|---:|---:|---:|
| Ideaal | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| Alleen uitleesruis (exact model) | 0.0095 | 0.0185 | 0.0118 | 0.9772 |
| Alleen resterende depolarisatie (128 trajecten) | 0.0685 | 0.1481 | 0.0700 | 0.7759 |
| Alleen gate-tijdrelaxatie (128 trajecten) | 0.0441 | 0.0913 | 0.0334 | 0.8700 |
| Depolarisatie + uitleesruis | 0.0696 | 0.1589 | 0.0751 | 0.7577 |
| Relaxatie + uitleesruis | 0.0441 | 0.1059 | 0.0408 | 0.8508 |
| Volledig Aer-model (eerdere 512 bitshots) | 0.0876 | 0.2676 | 0.0997 | 0.5896 |
| Hardware (eerdere 512 bitshots) | 0.1290 | 0.4226 | 0.1319 | 0.3551 |

Spincontrast is de projectie op het ideale spinpatroon; ideaal=1. Het is geen fideliteit.
RMSE is tegenover de exacte eindige circuitreferentie; component-RMSEs zijn niet optelbaar.

## Onzekerheid van de twee primaire componenten

- residual_depolarization_only: spin-RMSE 95%-interval [0.1307, 0.1731]; spincontrast [0.7432, 0.8062].
- gate_time_relaxation_only: spin-RMSE 95%-interval [0.0763, 0.1133]; spincontrast [0.8471, 0.8925].

2000 bootstrap-herhalingen binnen de vaste acht twirls. Puntgewijs, zonder modelonzekerheid.
De eerdere volledige Aer/hardware-rijen gebruiken 512 gemeten bitstrings: andere steekproefgrootte
en extra meetshotruis. Ze zijn context, geen identieke-precisie vergelijking met deze componenten.
Alleen uitleesruis is exact binnen het aangenomen onafhankelijke uitleesmodel.

Het oorspronkelijke volle ruiskanaal is gecontroleerd gereconstrueerd uit beide gatecomponenten.
Geen parameters zijn op hardware gefit. De uitsplitsing is afhankelijk van de gekozen Aer-noiseaannames.
Geen conclusie dat dezelfde component de echte hardwareafwijking veroorzaakt.
Geen idle-gap-relaxatie, crosstalk, leakage of coherente fouten toegevoegd.

Checks: 18 tests, 68 run-hashes, alle ruwe trajectwaarden gereproduceerd.
Tijden per component (Aer.run + resultaat ophalen): {"residual_depolarization_only": 106.35028107599646, "gate_time_relaxation_only": 197.53034394199858}

API: https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.library.save_expectation_value.html
