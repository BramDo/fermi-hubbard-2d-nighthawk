# Compacte TFLO-pilot: hardware-uitkomst

Job `dae5gat1ierc738lmg10` is DONE; werkelijk QPU-verbruik: 4 seconden. De providerlimiet was 5 seconden.
Alle 80 circuits en 5120 shots zijn ontvangen en geverifieerd. Geen herhaling.

Filtertolerantie 1, minimum 32 en ridge 0.001 waren vooraf vastgelegd. De zes nieuwe U=0-punten trainen de fit; validatie en U=8 niet.

| Tijd | Behouden / 512 | Methode | Lading RMSE | Spin RMSE | Doublon RMSE |
|---|---:|---|---:|---:|---:|
| 0.2 | 141 | raw | 0.1842 | 0.5319 | 0.1667 |
| 0.2 | 141 | postselected | 0.1424 | 0.4819 | 0.1385 |
| 0.2 | 141 | tflo | 0.0297 | 0.0869 | 0.0266 |
| 0.4 | 190 | raw | 0.1290 | 0.4226 | 0.1319 |
| 0.4 | 190 | postselected | 0.1305 | 0.4022 | 0.1128 |
| 0.4 | 190 | tflo | 0.0547 | 0.2051 | 0.0730 |

## Verplichte klassieke controle

Gepoolde Pauli-MSE: raw 0.264518; TFLO 0.033645; klassieke U=0-FLO-voorspelling 0.033533.
95%-interval voor raw-minus-TFLO MSE: {'low': 0.20828042948182843, 'high': 0.2631178086452509}.
95%-interval voor klassiek-minus-TFLO MSE: {'low': -0.005388573262687481, 'high': 0.004674262239608717}.
Inferentie volgens de vooraf vastgelegde grens: {'sampling_reliable': True, 'TFLO_better_than_raw': True, 'TFLO_better_than_classical_FLO_only': False}.

400/400 bootstrapreplicaties bruikbaar; 0 gestopt wegens te weinig behouden shots.
Onafhankelijke bestaande evaluator: maximaal verschil in centrale observabelen 0.000e+00.
Unit-tests en alle schattingen/replicaties zijn opgeslagen. Geen clipping, filterherselectie of oude fitcoefficienten.

De code is na hardwareuitvoering geschreven om het vooraf bevroren protocol uit te voeren, en voor analyse vastgelegd. Intervallen dekken sampling/refitting, niet TFLO-transferbias, Trotterfout of hardwaredrift tussen jobs. Referenties horen bij hetzelfde eindige Trottercircuit. Geen quantum-advantageclaim.
