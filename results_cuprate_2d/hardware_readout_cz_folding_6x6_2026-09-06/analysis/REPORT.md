# 6x6 readout + CZ-ZNE hardwarepilot

36 sites, 72 modes, T=0.4, U/t=8, t-prime/t=-0.25, two steps.
Raw4096 shots; readout5120; readout+ZNE13312. No equal-budget mitigation claim.

| Arm | N (target32) | N95% interval | Lowest onsite joint probability |
|---|---:|---|---:|
| raw_factor1 | 35.76929 | [35.64451904296875, 35.900146484375] | 0.22510 |
| readout_factor1 | 35.75664 | [35.62748082826066, 35.89290521998158] | 0.22195 |
| readout_cz_zne | 35.76763 | [35.56114746027543, 35.97554332948691] | 0.21356 |
| cz_zne_without_readout_diagnostic | 35.78019 | [35.584847005208346, 35.98152872721354] | 0.21444 |

No certified 6x6 reference: chi8/16/32 failed the stability screen.
Differences to MPS are discrepancies, not measured absolute quantum errors.
No local matched-accuracy speed advantage established.
Pointwise hybrid intervals: whole-shot conditional bootstrap at fixed twirls, shared independent Jeffreys readout-channel draws. Not simultaneous or coverage-certified; excludes drift, correlated SPAM, folding/extrapolation bias, Trotter error and MPS truncation.
