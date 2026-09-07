# Klassieke volledige 6x6-MPS-benchmark

Volledige fermionische t-t'-U-route, T=0,4 en twee netwerkstappen. Geen QPU-run.
Ryzen 5 3500U: 4 cores/8 threads; de bestaande WSL-omgeving ziet 3 CPU's.
Tijd omvat initialisatie, evolutie en lokale observabelen. Cold-worker tijd omvat ook imports.

| Grootte | chi | Threads | Rekenkern (s) | Cold worker (s) | N-afwijking |
|---|---:|---:|---:|---:|---:|
| 3x3 | 16 | 3 | 1.189 | 5.380 | 0 |
| 3x3 | 32 | 3 | 7.593 | 11.872 | -8.8818e-16 |
| 3x3 | 64 | 3 | 44.426 | 48.874 | 0 |
| 6x6 | 16 | 3 | 17.585 | 22.109 | -8.0414e-08 |
| 6x6 | 32 | 1 | 32.183 | 36.856 | 1.0207e-06 |
| 6x6 | 32 | 3 | 178.599 | 183.688 | 1.0629e-06 |
| 6x6 | 8 | 3 | 14.288 | 18.583 | 0 |

## Convergentie

[
  {
    "from_chi": 8,
    "to_chi": 16,
    "rmse_charge_spin_doublon": [
      0.01850804578789096,
      0.024683360298389558,
      0.008429594856288887
    ],
    "max_spin_difference": 0.0514490001865906,
    "screen_pass": false
  },
  {
    "from_chi": 16,
    "to_chi": 32,
    "rmse_charge_spin_doublon": [
      0.029369057398590685,
      0.11163567900227875,
      0.04176332391048592
    ],
    "max_spin_difference": 0.16519222992275528,
    "screen_pass": false
  }
]

Heuristische stabiliteitsscreen geslaagd: False. Geen gecertificeerde foutgrens.
Een timeout is geen bewijs dat alle klassieke methoden falen.
De 3-QPU-secondenmeting betrof3x3 en is geen6x6-snelheidsvergelijking.
Een lokale snelheidsclaim vereist dezelfde6x6-taak, nauwkeurigheid en expliciete timingdefinitie.
