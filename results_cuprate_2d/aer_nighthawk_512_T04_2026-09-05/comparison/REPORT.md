# Aer versus Nighthawk: matched 512-shot vergelijking

Een meetpunt: 3x3, U/t=8, T=0.4, 8 identieke twirls x 64 shots per dataset.
Geen nieuwe QPU-seconden. Geen TFLO, PEC of ZNE toegepast.

| Dataset / methode | Behouden | RMSE lading | RMSE spin | RMSE doublon |
|---|---:|---:|---:|---:|
| aer / raw | 512/512 | 0.0876 | 0.2676 | 0.0997 |
| aer / postselected_tolerance1 | 224/512 | 0.0843 | 0.2205 | 0.0818 |
| hardware / raw | 512/512 | 0.1290 | 0.4226 | 0.1319 |
| hardware / postselected_tolerance1 | 190/512 | 0.1305 | 0.4022 | 0.1128 |

RMSE is gemeten tegen de exacte ideale EINDIGE circuitreferentie, niet tegen continue tijd.
Ruwe Aer-hardware Pauli-RMSE: 0.18597.
Ruwe verschilcomponenten buiten de gelijktijdige 95%-band: [1, 2, 4, 5, 8, 10, 12, 14, 24].
Bandradius (vaste twirls): 0.18359; 2000 bootstrap-herhalingen.
Met twirl-resampling als gevoeligheidscheck: [4, 5, 12, 14, 24]; radius 0.25000.
Indices 0..17 zijn Z; 18..26 zijn onsite ZZ. Geen afwijking detecteren bewijst geen modelgelijkheid.

Aer-run plus ophalen van resultaten: 760.29 s totaal over acht blokken.
Exclusief imports, modelopbouw, ideale controles, opslag en analyse. Twee CPU-threads.

Beperkingen: oudere dagkalibratie, geen idle-gap-relaxatie, crosstalk, leakage, coherente fouten of drift.
Onzekerheidsbanden betreffen samples en de aangegeven twirlkeuze, niet deze modelonzekerheid.
Shot-resolutie, onafhankelijke halve batches, sitewaarden en alle intervallen staan in results.json.
Verificatie: 23 tests; 44 archiefhashes; 18 inputhashes.
