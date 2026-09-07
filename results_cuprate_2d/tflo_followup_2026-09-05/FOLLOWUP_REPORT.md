# TFLO vervolgstap: bestaande data en lokale circuitoptimalisatie

**Geen nieuwe QPU-job; extra QPU-verbruik 0 seconden.**

## 1. Minder gate-overhead, nog niet op hardware getest

X+SX-gates verminderd met 42.4%.
X-gates: 2088-2284 naar 546-588.
Diepte: 887-906 naar 623-637. Alle circuits behouden 1008 CZ-gates.
138 controles geslaagd, maximale 18-qubit-statevectorafwijking 2.944e-14; QPY exact herlaadbaar.

## 2. TFLO op de oude meetdata

Filter gekozen uitsluitend met zes U=0 trainingsinstellingen en twee U=0 validatiepunten. Gekozen: abs(N_up-4)+abs(N_down-4)<=1. Het minimum van 32 shots bleef staan. De oorspronkelijke strikte analyse blijft als mislukt bewaard.

| Tijd U=8 | Behouden shots | Charge RMSE voor -> na | Spin RMSE voor -> na | Doublon RMSE voor -> na |
|---|---:|---|---|---|
| 0.2 | 176 / 512 | 0.1840 -> 0.0236 | 0.5829 -> 0.0745 | 0.1725 -> 0.0164 |
| 0.4 | 157 / 512 | 0.1572 -> 0.0489 | 0.4792 -> 0.2047 | 0.1323 -> 0.0599 |

Gemiddelde kwadratische Pauli-fout over beide U=8-punten: 0.318025 -> 0.030717.
De verbetering ten opzichte van raw blijft positief in de 95%-bootstrapinterval inclusief herselectie van het filter op U=0. 400 replicaties, geen mislukte bootstrapfits. De precieze filterkeuze is niet stabiel: meerdere toleranties worden vaak gekozen.

## 3. Belangrijke klassieke controle

Een geheel klassieke U=0-FLO-voorspelling heeft op dezelfde U=8-doelen MSE 0.033533, tegenover 0.030717 voor TFLO.
De 95%-bootstrapinterval voor de extra winst boven die klassieke voorspelling is [-0.002738, 0.004927] en bevat nul.
**Dus: duidelijke foutreductie ten opzichte van de ruwe data, maar geen statistisch duidelijke extra winst boven deze goedkope klassieke voorspelling.** Dit is geen bewijs van quantum advantage.

## Grenzen en verificatie

Deze heranalyse is verkennend: U=8 werd niet gebruikt voor selectie/fitting, maar de ruwe U=8-resultaten waren al eerder bekeken. Bootstrap dekt geen systematische TFLO-transferbias. Referenties zijn dezelfde eindige Trotter-circuits. De opgeschoonde nieuwe circuits hebben geen nieuwe hardwaredata; hun gate-reductie is geen gemeten fidelitywinst.
59 archief-/reproductiechecks en 7 unit-tests geslaagd. Alle oorspronkelijke data en de indieningsblokkering zijn ongewijzigd.
De eerste optimalisatiepoging is bewaard; alleen de voortgangsopslag gaf een bestandsfout. De complete gevalideerde versie staat in optimization_v2.

[IBM: one-qubit-optimalisatie](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.transpiler.passes.Optimize1qGatesDecomposition).
