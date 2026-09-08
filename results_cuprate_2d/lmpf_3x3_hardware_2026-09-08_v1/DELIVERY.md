# 3x3 L-MPF toegepast; doorgangscontrole naar 6x6 mislukt

Datum: 8 september 2026. De mitigatie is werkelijk toegepast op de opgeslagen
3x3-hardwaremetingen, niet op opnieuw gegenereerde Aer-meetdata.
Job: `daem7r642tqs73autong`, backend `ibm_phoenix` (Nighthawk).
**Geen nieuwe QPU-job en geen 6x6-berekening gestart.**

## Uitkomst bij gelijk meetbudget

Doel: 3x3 spinvolle Hubbard, 18 qubits, Nup=Ndown=4, U/t=8, t'=-0.25,
T=0.4, twee symmetrische stappen. De referentie is het exacte eindige circuit,
niet de exacte continue Hamiltoniaandynamica. Spin betekent nup-ndown.

RMSE over de negen afzonderlijke sites, berekend uit de echte hardwaredata:

| Methode | Lading | Spin | Doublons |
| --- | ---: | ---: | ---: |
| Readoutcorrectie | 0.138041 | 0.358900 | 0.133527 |
| Readout + lineaire CZ-folding-ZNE | 0.183279 | 0.296204 | 0.135923 |
| Readout + L-MPF, chi=1, vaste ridge | 0.226652 | 0.259269 | 0.159875 |
| Readout + L-MPF, chi=1, zonder ridge | 0.301894 | 0.239860 | 0.220922 |
| Readout + kwadratische Richardson-ZNE | 0.248822 | 0.375946 | 0.289012 |

De vooraf als primair vastgelegde ridge is 1/56; de coëfficiënten zijn niet
op de exacte doelwaarden gefit. Vergeleken met lineaire ZNE is de primaire
spinfout ongeveer 12.5% kleiner, maar de ladingsfout 23.7% groter en de
doublonfout 17.6% groter. Daarom is het resultaat niet algemeen 'ok'.

Alle hoofdmethoden gebruiken 640 shots inclusief 128 gedeelde kalibratieshots.
Readout gebruikt 512 factor-1-shots. L-MPF en ZNE gebruiken 344/56/112 shots
op factoren 1/2/3; dat zijn per twirl 43/7/14 shots. De overige 21 factor-1-
shots per twirl zijn alleen voor de readoutbaseline. Alle 808 oorspronkelijke
shots blijven ongewijzigd bewaard. Gelijk shotbudget is niet gelijk CZ-budget.
Deze selectie wijkt af van de historische 512-shotanalyse; de oude tabellen
zijn niet overschreven en worden niet als hetzelfde experimentbudget gepresenteerd.

## Gepaard onzekerheidsoordeel

De tabel geeft baseline-RMSE minus primaire L-MPF-RMSE; positief is winst.
Intervallen: 2000 gepaarde, fixed-twirl-bootstrapreplicaties met één gedeelde
Jeffreys-uitleeskalibratietrekking per replicatie. De gedeelde factor-1-subset
en baseline-only-subset zijn afzonderlijk geresampled.

| Vergelijking | Lading: verschil [95%-interval] | Spin | Doublons |
| --- | --- | --- | --- |
| Readout minus L-MPF | -0.08861 [-0.14618; -0.05417] | +0.09963 [0.03856; 0.13914] | -0.02635 [-0.06641; -0.00363] |
| Lineaire ZNE minus L-MPF | -0.04337 [-0.06366; -0.02509] | +0.03693 [0.01059; 0.05500] | -0.02395 [-0.04452; -0.00887] |

Binnen deze onzekerheidsanalyse zijn zowel de spinwinst als de verslechtering
van lading en doublons zichtbaar. Dit is geen dekkingsbewijs: drift, gecorreleerde
ruis, systematische SPAM, TN-truncatie en ruis-modelbias ontbreken in de intervallen.

## Waarom geen 6x6?

De [vooraf vastgelegde controle](../../lmpf_2d/PLAN_3X3_TO_6X6.md) stond maximaal
0.02 absolute RMSE-verslechtering per familie toe tegenover beide baselines.
Lading en doublons overschrijden die grens. De vereiste spinverbetering is
wel aanwezig, maar heft die andere voorwaarden niet op. De physics-verificatieskill
vereist dat een mislukte controle wordt vastgelegd en niet wordt doorgeschoven.

Daarbij blijven deze waarschuwingssignalen staan:

- Minimaal gereconstrueerde lokale kans bij primaire L-MPF: -0.060244.
  Dit is een centrale schatting, geen bewijs dat de ware kans negatief is.
  Er is niet geclipt of gepostselecteerd.
- Zonder ridge lijkt N=7.995621 bijna exact 8, terwijl de ladingsprofielen
  juist veel slechter zijn. Met ridge is N=8.176946. N alleen is geen kwaliteitsmaat.
- Variatie van de aangenomen gate-ruissterkte met -30%/+30% verschuift een
  fysieke observable maximaal 0.088687. Dit is gevoeligheid, geen gekalibreerde CI.
- De ruis is nog een lokale depolariserende Lindblad-surrogaatbeschrijving uit
  opgeslagen gate-infideliteiten, geen geleerd en onafhankelijk gevalideerd model.
- Chi=1 naar chi=2-convergentie is niet aangetoond. Na de mislukte eerste
  nauwkeurigheidscontrole is die duurdere vervolgstap niet gestart.

## Implementatie en controles

- Alle 24 oorspronkelijke native doelcircuits verwerkt: acht twirls, drie
  CZ-foldingfactoren. Per circuit 1008/2016/3024 CZ, factor-1-twirl-0-diepte 629
  zonder eindmetingen (630 inclusief eindmetingen).
- Exacte verwijdering van ongebruikte apparaatdraden: 120 naar 18 actieve
  draden; geen fysieke gate of actieve ancilla weggelaten.
- Fysieke voorbereiding en eind-X-maskers meegenomen; readout wordt eerst
  geïnverteerd, daarna wordt het X-masker ongedaan gemaakt.
- Chi=1 als batched product-TN: lokale rank-one-SVD-truncatie, geen dichte
  4^18-operatorarray. Bond-one-netwerken hebben triviale loopcontracties;
  dit is niet de volledige, niet-triviale loopcorrectieproef uit de paper.
- De armoperator is het gemiddelde van acht twirls. Alle kruistermen tussen
  twirls zitten in de Gram-matrix; niet alleen de afzonderlijke twirl-Grams.
- 27 regressietests geslaagd. Drie nieuwe native ruisvrije statevectorchecks
  reproduceren de exacte referentie met maximaal 1.76e-14 afwijking.
- Onafhankelijke reconstructie: Gram-afwijking <=8.89e-16, ruwe-momentafwijking
  <=6.67e-16, optimizerstationariteit <=3.34e-16.
- Onafhankelijke quimb-chi=1-controle op één echte 18-qubit-observable: gelijke
  operator binnen de 1e-10 norm-kwadraattolerantie; nul niet-geconvergeerde BP-updates.
  Dit vervangt geen hogere-bond-validatie voor alle 27 observabelen.
- Conservatieve opgetelde truncatiegrens maximaal 4.797609: te ruim om
  nauwkeurigheid te certificeren. Minimale lokale relatieve Schmidt-gap 0.79729.

## Opgeslagen en reproduceerbaar

De volledige run duurde 61.970 seconden, de onafhankelijke audit 12.082 seconden
(imports/launcher niet inbegrepen). Geen vergelijking met de historische 6x6-
timingclaim en geen quantum advantage.

- [Runplan en bronhashes](plan.json).
- [Volledige resultaten en gevoeligheidsvarianten](summary.json).
- [Coëfficiënten](coefficients.json), [overlaps](overlaps.json), 80 opgeslagen
  productoperatorstaten onder `states/`, plus bootstrapdata.
- [Native circuit-identiteiten](native_inputs.json), [exacte controles](ideal_checks.json).
- [Onafhankelijke verificatie](verification/verification.json), [hashmanifest](sha256.json).

Commando's in WSL `Ubuntu-Preview-C`, bestaande `/home/bram/.venvs/qiskit`:

```sh
python -B test_lmpf_product.py
python -B lmpf_2d/archive_3x3.py --output NEW_DIRECTORY --budget-seconds 1200
python -B lmpf_2d/verify_archive_3x3.py NEW_DIRECTORY
```

Bronnen: [Robertson et al., L-MPF](https://arxiv.org/html/2609.05024v1),
[projectprotocol](../../theory/LMPF_PROTOCOL.md). Geen nieuwe QPU-uitvoering,
GitHub-push of Edukaizen-publicatie.
