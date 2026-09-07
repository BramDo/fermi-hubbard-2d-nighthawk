# Van 1D naar 2D Fermi-Hubbard: cuprate-route

Status: conceptverslag, 2026-07-03.

Dit verslag zet de tweede serie experimenten naast de eerdere 1D
Fermi-Hubbard reeks. De 1D reeks was een hardware/TDVP-validatie op een
keten; de nieuwe 2D reeks is een cuprate-georienteerde route met kleine
exacte validatie-rungs, IBM hardwarediagnostiek, Fire Opal waar beschikbaar,
en tensor-netwerk referenties voor grotere rungs.

Belangrijkste grens: de huidige 2D resultaten zijn diagnostische
validatie-data. Ze zijn geen claim van d-wave superconductiviteit, geen
cuprate-materiaalbewijs, en geen quantum-advantage claim.

## Samenvatting

De eerdere 1D snapshot in deze repo richtte zich op een 60-qubit /
30-site Fermi-Hubbard keten met 8 Trotter-stappen, IBM hardware, en
ITensorMPS TDVP referenties tot `chi=64`. De beste hardware-route haalde
tegen TDVP chi64 een charge RMSE van `0.01471` en spin RMSE van `0.03850`;
de chi64 TDVP run duurde lokaal `821.277 s`. Dat was een reproduceerbare
engineering- en validatie-snapshot, geen quantum-advantage claim.

De tweede serie bouwt dezelfde discipline op voor 2D:

- 2D square-lattice one-band Hubbard met `U/t=8`, `t'/t=-0.25`,
  open boundaries en hole-doped Neel/stripe initialisatie.
- 3x3 rung: exacte fixed-sector ED, TDHF, Gaussian/free baseline,
  IBM hardware, Fire Opal hardware, en tijdsverloop tot step 4.
- 4x4 rung: quimb MPS circuit-baseline voor de shallow circuitfamilie,
  IBM hardware op `ibm_marrakesh`, en Fire Opal abstract input geprobeerd.

De 3x3 resultaten laten zien dat Fire Opal veel schoner is dan directe IBM,
maar sector-survival daalt met tijd. De 4x4 directe IBM run is voltooid,
maar blijft duidelijk verwijderd van de MPS/local baselines.

## 1. Theorie: 2D Hubbard en cuprates

Het one-band 2D Hubbard-model is een minimale roosterbeschrijving van
interacterende elektronen:

```text
H =
  - t   sum_<i,j>,sigma (c^dagger_{i,sigma} c_{j,sigma} + h.c.)
  - t'  sum_<<i,j>>,sigma (c^dagger_{i,sigma} c_{j,sigma} + h.c.)
  + U   sum_i n_{i,up} n_{i,down}
  - mu  sum_i,sigma n_{i,sigma}.
```

Hier is `t` nearest-neighbor hopping, `t'` next-nearest-neighbor hopping,
`U` de onsite repulsie, en `mu` de chemische potentiaal. Voor cuprates is
dit model interessant omdat de CuO2-vlakken effectief tweedimensionaal zijn
en sterke correlaties, antiferromagnetisme, hole doping en mogelijke d-wave
pairing centraal staan. Het model is echter een vereenvoudiging: echte
cuprates hebben meerdere orbitalen, fononen, disorder, materiaalafhankelijke
parameters en eindige-temperatuur effecten.

De huidige metingen gebruiken diagonale Z-basis observables:

- `charge_i = n_{i,up} + n_{i,down}`
- `spin_z_i = n_{i,up} - n_{i,down}`
- `double_occupancy_i = n_{i,up} n_{i,down}`
- nearest-neighbor charge/spin-z bond correlations

Deze observables zijn geschikt voor de eerste validatie van charge/spin
dynamica en sector leakage. Ze meten nog geen off-diagonal d-wave pairing.
Daarvoor zijn aparte basisrotaties, correlatorcircuits of tomografische
metingen nodig.

## 2. Externe context: van 1D naar Google/Willow 2D

De 1D context is inmiddels ook extern relevant. Hartnett et al.
rapporteren in arXiv:2605.04025 grootschalige 1D Fermi-Hubbard dynamica
met tot 120 qubits en vergelijking met TDVP tot `chi=4096` in regimes waar
hardware en klassieke benaderingen nog kwantitatief overlappen.

Voor 2D is de belangrijkste recente referentie Alam et al.,
arXiv:2510.26845. Zij rapporteren programmeerbare digitale simulatie van
2D Fermi-Hubbard dynamica met 72 qubits op Google's Willow processor, met
lattice sizes tot `6x6`. Hun validatie combineert exact rekenen waar dat nog
kan met tensor-network en operator-propagation methoden waar exact rekenen
niet meer haalbaar is. De bijbehorende Zenodo dataset bevat raw shots en
expectation values per fysisch systeem.

Dit plaatst onze route in de juiste schaal:

- Google/Phasecraft: geoptimaliseerde 2D stack, Willow, tot `6x6`, externe
  benchmark met tensor/operator baselines.
- Deze repo: stapsgewijze IBM/Fire Opal validatie, eerst `3x3`, daarna
  `4x4`, met expliciete sector-diagnostiek en lokale baselines.

De juiste ambitie is dus niet om blind naar `6x6` te submitten, maar om de
stack te bouwen die een `6x6` run zinvol maakt: ondiepere circuits,
betere fermion-routing, tensor/operator baselines, en duidelijke
observable-comparison.

Bronnen:

- Alam et al., "Programmable digital quantum simulation of 2D
  Fermi-Hubbard dynamics using 72 superconducting qubits",
  arXiv:2510.26845, https://arxiv.org/abs/2510.26845
- Dataset bij Alam et al., Zenodo 17881822,
  https://zenodo.org/records/17881822
- Hartnett et al., "Fast, accurate, high-resolution simulation of
  large-scale Fermi-Hubbard models on a digital quantum processor",
  arXiv:2605.04025, https://arxiv.org/abs/2605.04025

## 3. Onze implementatie: 3x3 validatie-rung

De eerste 2D rung gebruikt een `3x3` rooster met een hole:

- sites/qubits: `9 / 18`
- sector: `N_up=N_down=4`
- Hamiltonian: full Hubbard en t-only variant
- exact fixed-sector ED dimension: `15876`
- full Hubbard Hamiltonian nnz: `368046`
- circuitfamilie voor hardware: `number_preserving_t_only`

De rol van 3x3 is niet cuprate-fysica op schaal. De rol is validatie:
dezelfde observables, dezelfde configuratie, exact ED mogelijk, en hardware
tegen een lokale referentie vergelijken.

### 3.1 Exact ED, TDHF en Gaussian/free over tijd

Exact full ED houdt totale charge en spin-z behouden en laat de verwachte
vroege spin-melting en doublon-vorming zien:

| step | total charge | total spin-z | mean abs spin-z | mean doublon |
|---:|---:|---:|---:|---:|
| 0 | 8.000000 | 0.000000 | 0.888889 | 0.000000 |
| 1 | 8.000000 | 0.000000 | 0.855116 | 0.016223 |
| 2 | 8.000000 | 0.000000 | 0.778109 | 0.049209 |
| 3 | 8.000000 | -0.000000 | 0.707763 | 0.069466 |
| 4 | 8.000000 | -0.000000 | 0.674849 | 0.064354 |

RMSE tegen exact full:

| step | source | charge RMSE | spin-z RMSE | doublon RMSE |
|---:|---|---:|---:|---:|
| 1 | exact t-only | 0.000519 | 0.000896 | 0.000079 |
| 2 | exact t-only | 0.001871 | 0.003245 | 0.000982 |
| 3 | exact t-only | 0.013111 | 0.006454 | 0.003472 |
| 4 | exact t-only | 0.031148 | 0.009996 | 0.007165 |
| 1 | TDHF | 0.000004 | 0.000029 | 0.000040 |
| 2 | TDHF | 0.000196 | 0.001375 | 0.001822 |
| 3 | TDHF | 0.001202 | 0.008724 | 0.011952 |
| 4 | TDHF | 0.003642 | 0.019529 | 0.032194 |
| 1 | Gaussian/free | 0.000378 | 0.001924 | 0.000889 |
| 2 | Gaussian/free | 0.005167 | 0.026965 | 0.011859 |
| 3 | Gaussian/free | 0.019970 | 0.109488 | 0.044513 |
| 4 | Gaussian/free | 0.042469 | 0.254813 | 0.093432 |

Interpretatie:

- TDHF is zeer goed op de vroege diagonale observables, maar doublon loopt
  vanaf step 3/4 weg.
- t-only blijft op step 1/2 dicht bij full Hubbard, maar interaction effects
  worden zichtbaarder op langere tijd.
- Gaussian/free divergeert het snelst, vooral in spin-z en doublon.

### 3.2 3x3 hardware: IBM en Fire Opal

De shallow route verminderde de IBM-transpiled 3x3 step-1 resources naar:

- depth `167`
- two-qubit count `159`
- two-qubit depth `52`

Fire Opal qelib step 1 gebruikte:

- exported depth `25`
- CX count `66`
- two-qubit depth `10`

Hardware-diagnostiek tegen exact full:

| step | route | exact-sector survival | charge RMSE | spin-z RMSE | doublon RMSE |
|---:|---|---:|---:|---:|---:|
| 1 | IBM exact-sector | 0.224609 | 0.072170 | 0.098797 | 0.038610 |
| 1 | Fire Opal exact-sector | 0.567568 | 0.012651 | 0.019293 | 0.010273 |
| 2 | IBM exact-sector | 0.137695 | 0.123534 | 0.233135 | 0.073125 |
| 2 | Fire Opal exact-sector | 0.332692 | 0.035551 | 0.074967 | 0.027467 |
| 3 | IBM exact-sector | 0.146484 | 0.079577 | 0.182239 | 0.036406 |
| 3 | Fire Opal exact-sector | 0.216972 | 0.031717 | 0.074023 | 0.023461 |

Conclusie voor 3x3:

- Fire Opal is systematisch beter dan directe IBM.
- Sector survival daalt met tijd, vooral bij Fire Opal van `0.568` naar
  `0.217` van step 1 naar step 3.
- De hardware-resultaten zijn nuttig als ruis- en sector-diagnostiek, maar
  niet als fysisch eindresultaat.

## 4. 4x4 rung: hardware plus tensor baseline

De volgende rung gebruikt `4x4` met twee holes:

- sites/qubits: `16 / 32`
- expected sector: `N_up=N_down=7`
- circuitfamilie: `number_preserving_t_only`
- step/dt/time: `1 / 0.1 / 0.1`
- backend: `ibm_marrakesh`

### 4.1 4x4 circuitdiepte

De 4x4 dry-run gaf:

| route | logical depth | transpiled IBM depth | two-qubit gates | two-qubit depth |
|---|---:|---:|---:|---:|
| 3x3 IBM step 1 reference | 8 | 167 | 159 | 52 |
| 4x4 IBM step 1 | 8 | 199 | 341 | 65 |
| 4x4 Fire Opal abstract input | 8 | not hardware-compiled | 64 logical | 5 logical |

Het aantal two-qubit gates verdubbelt ongeveer ten opzichte van 3x3, maar de
two-qubit depth groeit veel minder hard door parallelisme.

### 4.2 MPS tensor baseline

Voor 4x4 is geen exacte ED meer praktisch als algemene route. Daarom is een
quimb MPS circuit-baseline toegevoegd voor dezelfde shallow circuitfamilie.
Dit is geen full Hamiltonian TDVP, maar wel een apples-to-apples
circuitreferentie voor de hardware-output.

| max bond | observed max bond | elapsed s | occupation RMSE vs previous | total charge | total spin-z | mean doublon |
|---:|---:|---:|---:|---:|---:|---:|
| 32 | 32 | 13.497 | None | 14.000000 | 0.000000 | 0.020073 |
| 64 | 64 | 49.455 | 0.000202737 | 14.000000 | 0.000000 | 0.020170 |

De `chi32 -> chi64` occupation RMSE is ongeveer `2.0e-4`. Voor deze korte
shallow step is de MPS-rung dus numeriek stabiel genoeg om als lokale
referentie te dienen.

Lokale baselines tegen MPS chi64:

| source | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---:|---:|---:|
| TDHF | 0.000660 | 0.002011 | 0.000995 |
| Gaussian/free | 0.000955 | 0.000917 | 0.000088 |

### 4.3 4x4 IBM hardware-resultaat

De 4x4 IBM job:

- job id: `d93v9a6vtlqs73ftm6mg`
- backend: `ibm_marrakesh`
- status: `DONE`
- shots: `1024`
- main transpiled resources: depth `199`, two-qubit count `341`,
  two-qubit depth `65`

Hardware summary:

| profile | total charge | total spin-z | mean abs spin-z | mean doublon |
|---|---:|---:|---:|---:|
| raw | 13.766602 | -0.340820 | 0.650818 | 0.072632 |
| readout-corrected | 13.881690 | -0.242608 | 0.685372 | 0.064137 |
| MPS chi64 | 14.000000 | 0.000000 | 0.833332 | 0.020170 |

RMSE tegen MPS chi64:

| source | profile | charge RMSE | spin-z RMSE | doublon RMSE |
|---|---|---:|---:|---:|
| IBM | raw | 0.119908 | 0.218926 | 0.059685 |
| IBM | readout-corrected | 0.130838 | 0.190883 | 0.056986 |
| IBM | exact-sector | 0.097011 | 0.123450 | 0.044959 |

Particle-sector survival:

| profile | kept shots | total shots | kept fraction |
|---|---:|---:|---:|
| exact sector `N_up=N_down=7` | 133 | 1024 | 0.129883 |
| near sector L1 <= 1 | 462 | 1024 | 0.451172 |
| near sector L1 <= 2 | 762 | 1024 | 0.744141 |

Interpretatie:

- Directe IBM 4x4 hardware is voltooid, maar ver van de MPS/local
  baselines.
- Exact-sector postselectie verbetert de RMSE duidelijk, maar houdt slechts
  13% van de shots over.
- Dit is een nuttige diagnostische rung voor noise/sector leakage en
  circuit-schaalbaarheid, niet een fysisch eindresultaat.

### 4.4 Fire Opal status

Fire Opal is geprobeerd met abstract/native input voor dezelfde 4x4 route.
De QASM manifesten waren lokaal parsebaar, maar `fireopal.execute` werd
geblokkeerd door een Q-CTRL daily API limit voordat een `action_id` werd
teruggegeven. Er is dus geen Fire Opal 4x4 hardware-resultaat.

## 5. Conclusies en volgende stap

De tweede serie heeft de 2D route in drie lagen opgebouwd:

1. Theorie en observable-definitie voor een 2D cuprate-achtige Hubbard route.
2. 3x3 validatie met exact ED, TDHF, Gaussian/free, IBM en Fire Opal.
3. 4x4 opschaling met MPS circuit-baseline en directe IBM hardware.

De technische conclusie is scherp:

- 3x3 is goed als exact validatielab.
- Fire Opal is op 3x3 duidelijk beter dan directe IBM.
- 4x4 directe IBM is uitvoerbaar qua diepte, maar ruis/sector leakage is nog
  dominant.
- Tensor-baselines zijn noodzakelijk vanaf 4x4; TDHF alleen is niet genoeg
  als uiteindelijke referentie.

De beste volgende stap is niet meteen een grotere hardware-run. De beste
volgende stap is:

1. Fire Opal 4x4 opnieuw submitten zodra de Q-CTRL API limit vrij is.
2. De 4x4 MPS baseline uitbreiden naar een convergentieladder, bijvoorbeeld
   `chi=32,64,128`.
3. De circuitfamilie verder verlagen of naar betere fermion-routing/fSWAP
   brengen.
4. Pas daarna `4x4 step 2` of `6x6` dry-runs vergelijken.

## Artifacts

Belangrijkste lokale bestanden:

- `docs/paper_draft.md`
- `README.md`
- `results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1/time_sweep_steps4/observable_time_sweep/cuprate_2d_time_sweep_report.md`
- `results_cuprate_2d/validation_ladder_steps1/cuprate_4x4_holes2_steps1/mps_shallow_t_only_steps1/cuprate_2d_mps_report.md`
- `results_cuprate_2d/validation_ladder_steps1/cuprate_4x4_holes2_steps1/ibm_hardware_steps1_shallow_t_only_best_layout/cuprate_2d_ibm_hardware_summary.md`
- `results_cuprate_2d/validation_ladder_steps1/cuprate_4x4_holes2_steps1/observable_comparison_shallow_t_only_steps1_vs_mps/cuprate_2d_observable_comparison.md`
- `results_cuprate_2d/validation_ladder_steps1/cuprate_4x4_holes2_steps1/sector_conditioned_shallow_t_only_steps1_vs_mps/sector_conditioned_report.md`
