# PA-ancilla pilot 6x6

Volledig lokaal. Geen nieuwe hardware-run. Correctness-first PA, niet de XYZ-diepte uit het paper.

Encoding: 72 fermionmodi + 36 ancillas = 108 qubits.
11 tests geslaagd; alle 25 loopconstraints en 72 bezettingen van de volledige voorbereiding gecontroleerd.
De resterende 11 hulpvrijheidsgraden zijn deterministisch vastgelegd door de Clifford-voorbereiding.
Op 2x2 zijn alle Hubbardtermen in beide pariteitssectoren tegen onafhankelijke JW-tekens gecontroleerd.
Geen volledige 108-qubit-statevector gesimuleerd.

| Kandidaat | CZ | CZ-lagen | Totale diepte | Duur, microseconden |
|---|---:|---:|---:|---:|
| preparation_only | 852 | 375 | 870 | 39.320 |
| network_seed9 | 23138 | 6288 | 14603 | 676.136 |
| network_seed9_twirl | 23138 | 6288 | 19635 | 722.944 |
| layered_seed9 | 21670 | 3745 | 8733 | 408.408 |
| layered_seed9_twirl | 21670 | 3745 | 11752 | 436.352 |
| layered_seed27 | 21337 | 3404 | 7969 | 372.268 |
| layered_seed27_twirl | 21337 | 3404 | 10772 | 397.968 |

Preparation-only is apart gecompileerd en mag niet van de totale tijd worden afgetrokken.
Alle andere kandidaten bevatten voorbereiding, volledige t-t-prime-U evolutie en data-uitlezing.
Twirl-kandidaten bevatten een enkele controle-twirl, geen complete readout/ZNE-meetbatch.
Duren zijn geschat met de opgeslagen kalibratie, zonder reset/rep_delay/queue; geen live metingen.

## Interpretatie

Network behoudt de oorspronkelijke fysieke eventvolgorde en het ideale eindige-stappendoel.
Layered behoudt alle termen, tijd en symmetrische orde, maar verandert niet-commuterende termvolgordes.
Daarvoor is een nieuwe circuitgematchte klassieke referentie en Trotter-convergentiecheck nodig.
Een lager aantal abstracte lagen is geen bewijs van betere hardware-observabelen.
De PA-tekening is 18x6, de opgeslagen chip 10x12. Hardware-routing is daarom expliciet meegenomen.
De physics-skill stuurde de teken-, code-subruimte-, voorbereidings- en mappingcontroles.

## Afwijkingen van plan

Auto-fixed integration bug: v1 treated compact_bound output as a circuit instead of (circuit,proof).
A v2 regression test incorrectly supplied a non-native H gate to a native-only verifier; fixed to SX.
The failed v1/v2 outputs and source snapshots remain intact. No model-physics tests failed.
Within PA, shared-parity paired hopping synthesis was added and checked against exact local matrix exponentials and full small circuits.
Geen modelvereenvoudiging. De laagdiepe XYZ-synthese is nog niet geimplementeerd; de native cijfers gelden alleen voor deze correctness-first synthese.

Bron: https://arxiv.org/html/2302.01862v3 (PA, secties4/5.2; native-gate caveat sectie6).
