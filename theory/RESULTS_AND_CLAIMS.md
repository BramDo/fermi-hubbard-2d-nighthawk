# Resultaten- en claimregister

Peildatum: 7 september 2026. De kleine-schaal ambitie is een lokale
computerbenchmark, geen bewijs dat iedere klassieke methode wordt verslagen.

## Vastgelegde timing

| Record | Waarde | Betekenis |
|---|---:|---|
| classical_full_6x6_mps_T04_chi64_v1 | 150.819180137 s | klassieke rekenkern |
| dezelfde worker | 156.905496582 s | inclusief imports, exclusief launcher |
| daesvo51ierc738mji3g | 8 QPU s | aparte TFLO/DD-job |
| daf6foe42tqs73avhoeg | 7 QPU s | gehele original/compact-job |
| 150.819180137 / 8 | 18.8524 | verhouding van bovenstaande klokken |
| 150.819180137 / 7 | 21.5456 | verhouding van bovenstaande klokken |

Goedgekeurde formulering: circa 20x minder geregistreerde QPU-tijd dan
de rekenkerntijd van de huidige lokale klassieke baseline. Niet aangetoond:
20x kortere totale doorlooptijd, gelijke-nauwkeurigheidsvoordeel, chi128-winst,
beyond-classical advantage of een beste-resultaatclaim tegenover Google.
De laatste job had 76 PUBs x512 shots; niet 512 shots voor de hele job.
Het provider running-to-finished-interval was circa181s, exclusief wachtrij.
De klassieke timing had gelijktijdig ander lokaal werk en was niet geisoleerd.

## Laatste observabelen

| Methode | N | D/site | Spinprofiel-RMS | RMS lading/spin/D tegen chi64 |
|---|---:|---:|---:|---|
| Original TFLO | 31.39633 | .090130 | .656826 | .083889 / .091851 / .050805 |
| Compact TFLO | 31.23064 | .077194 | .671282 | .109304 / .125864 / .064116 |
| Chi64 | 31.9999992 | .087896 | .703456 | referentie, niet gecertificeerd |

Holdouts: beide armen gescreend en mislukt. Minimaal gereconstrueerde
lokale kans: original -.077303; compact -.092726. Niet afgeknipt.
Alle controles zonder targethardware-input blijven in de bronanalyse.
De oudste DD-aan TFLO-cijfers horen bij een andere job; niet mengen.
De laatste gepaarde run had geen DD, ZNE, PEC of postselectie.

## Model en referentie

6x6 open,72 modi,N32(16+16),t1,t'-.25,U8,T.4,twee symmetrische stappen.
Spin=n_up-n_down. De chi64-referentie is voor het eindige circuit.
Chi32->64 en tijdstapconvergentie vormen aparte controles; chi128 is niet
uitgevoerd. Exact N32 is een modelconstraint, niet een gemeten hardwarewaarde.

## Bronnen

- results_cuprate_2d/hardware_compact_tflo_2026-09-07_v1/analysis/summary.json
- results_cuprate_2d/hardware_compact_tflo_2026-09-07_v1/provider_metrics.json
- results_cuprate_2d/hardware_tflo_dd6_2026-09-06_v1/provider_metrics.json
- results_cuprate_2d/classical_full_6x6_mps_T04_chi64_v1/summary.json
- results_cuprate_2d/google_conversion_2026-09-07_v1/comparison.json

Verdere hardwaregebruikstoestemming: geen. Publicatiestatus serie3: gepubliceerd
op 2026-09-07 onder [2D Local Quantum Advantage](https://edukaizen.nl/2d-local-quantum-advantage/).
De repository blijft prive; dit verandert de validatiestatus van de resultaten niet.
