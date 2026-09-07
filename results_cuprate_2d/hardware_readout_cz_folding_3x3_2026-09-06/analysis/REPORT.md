# Hardware: readout + CZ-folding ZNE

Job `daem7r642tqs73autong`, backend `ibm_phoenix`.
Alle 808 nieuwe shots ontvangen. Analytische hoofdarmen elk 512 shots inclusief kalibratie.

| Methode | Lading-RMSE | Spin-RMSE | Doublon-RMSE |
|---|---:|---:|---:|
| raw512 | 0.13884 | 0.36824 | 0.13723 |
| readout384_cal128 | 0.14040 | 0.36699 | 0.13136 |
| readout_CZ_ZNE_PRIMARY | 0.19216 | 0.26604 | 0.13309 |
| CZ_ZNE_no_readout_DIAGNOSTIC | 0.18829 | 0.27657 | 0.13501 |

Primaire spin-RMSE-afname: 0.10220; hybride95%-interval [0.03974, 0.14081].
Dit combineert gepaarde shot-bootstrap en kalibratieposterior; geen volledige systematische foutmarge.
Lading, doublonen, deeltjesgetal en fysieke grenzen staan onverkort in results.json.
Geen postselectie, clipping, PEA, PEC of TFLO toegepast.
Gelijke shots zijn niet gelijke poort-/tijdkosten; geen quantum advantage aangetoond.
Providergebruik: {"qpu_charge_time_seconds": 3, "status": "complete"}
