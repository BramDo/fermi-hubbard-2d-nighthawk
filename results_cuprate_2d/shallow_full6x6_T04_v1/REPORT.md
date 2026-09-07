# Ondiepere 6x6-circuits: alleen offline getest

Zelfde Hamiltoniaan, fermiontekens, oorspronkelijke interactievolgorde en T=0,4. Geen QPU-job.
De oorspronkelijke meetdata en circuits zijn niet gewijzigd.

Routing vóór compilatie: 9200/10224 blokken bevatten geen fysische interactie.
Op de geselecteerde qubits zijn 108 CZ-verbindingen beschikbaar; de oude route gebruikt een pad van 71 verbindingen.
Dit zijn routingdiagnostieken, geen berekende fideliteiten.

| Circuit | CZ | X+SX | Totale diepte | CZ-diepte | Tijd (µs, snapshot) |
|---|---:|---:|---:|---:|---:|
| original_native_no_twirls | 15400 | 19557 | 1808 | 564 | 67.052 |
| original_factor1_twirl0 | 15400 | 50490 | 3241 | 564 | 99.732 |
| compact_factor1_twirl0 | 15400 | 26224 | 2030 | 564 | 72.252 |
| original_factor2_twirl0 | 30800 | 50490 | 3896 | 1416 | 148.148 |
| compact_factor2_twirl0 | 30800 | 26224 | 2723 | 1416 | 123.500 |
| original_factor3_twirl0 | 46200 | 50490 | 4369 | 1692 | 176.436 |
| compact_factor3_twirl0 | 46200 | 26224 | 3158 | 1692 | 148.956 |
| compact_factor1_twirl1 | 15400 | 26185 | 2022 | 564 | 71.812 |
| compact_factor1_twirl2 | 15400 | 26204 | 2036 | 564 | 72.572 |
| compact_factor1_twirl3 | 15400 | 26166 | 2025 | 564 | 72.412 |
| compact_factor1_twirl4 | 15400 | 26375 | 2020 | 564 | 72.852 |
| compact_factor1_twirl5 | 15400 | 26251 | 2040 | 564 | 72.492 |
| compact_factor1_twirl6 | 15400 | 26230 | 2040 | 564 | 72.332 |
| compact_factor1_twirl7 | 15400 | 26180 | 2044 | 564 | 72.652 |
| sparse_left | 25762 | 42491 | 6422 | 2002 | 226.244 |
| sparse_look4 | 18720 | 31725 | 10045 | 3423 | 357.904 |
| sparse_look12 | 14168 | 24893 | 7722 | 2555 | 274.520 |

Snelste kandidaat volgens opgeslagen kalibratie: compact_factor1_twirl0.
Sparse varianten behouden een bekende laatste fermionpermutatie: gebruik hun opgeslagen logical_output_layout en readout_mask, nooit de oude uitleesmapping.
De klassieke exacte doelobservabelen blijven gelijk; een χ-afgekapt MPS-resultaat blijft een benadering.
Geen lagere hardwarefout of quantumvoordeel aangetoond. Verse ISA/budgetcontrole en nieuwe expliciete toestemming blijven vereist.
Geen algemene optimalisatie na CZ-folding: die kan de ingevoegde identiteitsparen verwijderen.
De één-qubit-opschoning controleert juist dat alle CZ-poorten en hun volgorde per draad behouden blijven.
