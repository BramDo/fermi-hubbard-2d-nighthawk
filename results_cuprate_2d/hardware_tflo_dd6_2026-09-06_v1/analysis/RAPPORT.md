# 6x6 TFLO + DD: vaste pilotanalyse

Job daesvo51ierc738mji3g. Geen tweede hardwarejob. Alle 38912 shots geverifieerd.

TFLO-holdoutscreen DD uit/aan: [False, False].
Als de screen niet slaagt zijn de TFLO-uitkomsten DIAGNOSTIC_UNVALIDATED, geen herstelde observabelen.

| DD | Methode | N | RMS lading | RMS spin | RMS doublon | Minimum lokale kans |
|---|---|---:|---:|---:|---:|---:|
| False | raw | 35.5635 | 0.2744 | 0.7025 | 0.1599 | 0.2085 |
| False | readout | 35.5737 | 0.2752 | 0.7028 | 0.1601 | 0.2053 |
| False | readout_tflo | 32.5622 | 0.0930 | 0.0804 | 0.0577 | -0.0881 |
| True | raw | 35.5830 | 0.2805 | 0.7031 | 0.1625 | 0.2192 |
| True | readout | 35.5934 | 0.2815 | 0.7034 | 0.1628 | 0.2168 |
| True | readout_tflo | 32.0784 | 0.0717 | 0.0914 | 0.0516 | -0.1052 |

Afstanden hierboven tegenover niet-gecertificeerde chi64, geen exacte hardwarefouten.
Readout en handmatige twirling in beide armen; DD-X-X-pulsen expliciet in de aan-circuits.
TFLO zonder tijdfeature, uitsluitend zes U=0-trainingspunten per DD-arm; geen filtering of clipping.
Alle holdouts, klassiek-only vergelijkingen, onzekerheden en fitdiagnostiek staan in summary.json.

Whole-shot conditional bootstrap at fixed twirls plus shared independent readout-channel Beta draws and training refit. Excludes drift, correlated SPAM, TFLO transfer bias, Trotter and MPS truncation. Not simultaneous or coverage-certified.

## Onafhankelijke rekencontroles

```json
{
  "independent_pair_inversion_max_abs": 2.220446049250313e-16,
  "integer_popcount_max_abs": 0.0,
  "independent_affine_lstsq_max_abs": 4.218847493575595e-14,
  "training_U0_only": true,
  "heldout_excluded_from_fit": true,
  "target_reference_excluded_from_fit": true,
  "records": 76,
  "shots": 38912,
  "all_source_hardware_hashes_verified": true
}
```

Physics- en veilige-API-skills bewaakten onafhankelijke validatie, de budgetgrens en behoud van ruwe data.
Geen quantum advantage aangetoond.
