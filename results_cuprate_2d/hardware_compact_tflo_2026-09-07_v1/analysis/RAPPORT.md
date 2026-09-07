# 6x6: origineel versus compact

Job daf6foe42tqs73avhoeg; 38.912 shots geverifieerd.

TFLO-holdoutscreen origineel/compact: [False, False].

| Circuit | Methode | N | RMS lading | RMS spin | RMS doublon | Minimum lokale kans |
|---|---|---:|---:|---:|---:|---:|
| original | raw | 35.4634 | 0.2750 | 0.7015 | 0.1571 | 0.2192 |
| original | readout | 35.4928 | 0.2761 | 0.7017 | 0.1574 | 0.2166 |
| original | readout_tflo | 31.3963 | 0.0839 | 0.0919 | 0.0508 | -0.0773 |
| compact | raw | 35.8682 | 0.2807 | 0.7072 | 0.1648 | 0.2227 |
| compact | readout | 35.9086 | 0.2822 | 0.7075 | 0.1654 | 0.2197 |
| compact | readout_tflo | 31.2306 | 0.1093 | 0.1259 | 0.0641 | -0.0927 |
| original | fit_without_target_hardware_input | 32.0006 | 0.0293 | 0.0577 | 0.0114 | 0.0068 |
| compact | fit_without_target_hardware_input | 32.0007 | 0.0293 | 0.0577 | 0.0114 | 0.0068 |

U8-afstanden tegenover niet-gecertificeerde chi64, geen exacte hardwarefouten.
Geen clipping, postselectie, extra DD, ZNE of PEC. TFLO gebruikt uitsluitend zes U0-trainingspunten.
De controle zonder doelhardware-input gebruikt dezelfde fit met het gemiddelde trainingsinput.
Bij falende holdouts blijven TFLO-uitkomsten DIAGNOSTIC_UNVALIDATED.

## Primaire gepaarde holdoutvergelijking

| Tijd | Methode | Winst lading | Winst spin | Winst doublon |
|---|---|---:|---:|---:|
| 0.2 | raw | -0.0057 | +0.0045 | -0.0066 |
| 0.2 | readout | -0.0060 | +0.0047 | -0.0068 |
| 0.2 | readout_tflo | -0.0272 | -0.0319 | -0.0116 |
| 0.4 | raw | -0.0103 | -0.0033 | -0.0080 |
| 0.4 | readout | -0.0107 | -0.0033 | -0.0084 |
| 0.4 | readout_tflo | +0.0060 | +0.0316 | -0.0065 |

Positief betekent lagere RMS-fout voor compact; onzekerheidsintervallen staan in summary.json.
Conditional whole-shot bootstrap at fixed twirls, shared independent readout Beta draws and training refit. Excludes drift, correlated SPAM, TFLO transfer bias, Trotter and MPS truncation; not simultaneous or coverage-certified.

## Onafhankelijke controles

```json
{
  "independent_readout_pair_inversion_max_abs": 4.440892098500626e-16,
  "independent_integer_popcount_max_abs": 0.0,
  "independent_augmented_lstsq_max_abs": 2.353672812205332e-14,
  "training_U0_only": true,
  "holdouts_and_target_excluded_from_fit": true,
  "shots": 38912,
  "records": 76,
  "old_archives_not_modified": true
}
```

De physics- en veilige-API-skills bewaakten de budgetgrens, controles en archivering. Geen quantum advantage aangetoond.
