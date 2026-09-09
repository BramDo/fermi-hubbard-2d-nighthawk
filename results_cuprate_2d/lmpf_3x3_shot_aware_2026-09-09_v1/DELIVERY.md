# Shotafhankelijke regularisatie: minder versterkte ruis, nog geen gevalideerde winst

9 september 2026. Een enkele vooraf vastgelegde shotafhankelijke straf is
getest op dezelfde centrale 3x3-twirl-0-data als de vorige pilot:
job `daem7r642tqs73autong`, `ibm_phoenix`, 43/7/14 targetshots,
dezelfde subset en dezelfde 128 readoutkalibratieshots. **Geen nieuwe QPU-job.**

De nieuwe puntschattingen zijn voor alle drie grootheden beter dan de oude
vaste-ridge L-MPF. Maar de doublonschatting blijft negatief, en geen van de
gepaarde verbeteringsintervallen sluit nul uit. Geen doorgang naar 6x6.

## Primaire waarden, allemaal bij 192 toegewezen gearchiveerde shots

De tabel gaat over de centrale site, niet over totale lattice-lading N.
De referentie is exact voor het eindige ideale circuit.

| Methode | Centrale lading | Centrale spin | Centrale doublon |
| --- | ---: | ---: | ---: |
| Exacte circuitreferentie | 0.404671 | -0.362021 | 0.009685 |
| Readout-only | 0.571533 | -0.079346 | 0.043825 |
| Readout + lineaire ZNE | 0.271179 | -0.460012 | -0.183805 |
| Vorige L-MPF, ridge 1/56 | -0.029469 | -0.712862 | -0.309473 |
| Nieuwe shotafhankelijke L-MPF | 0.221461 | -0.527273 | -0.161307 |

Readout gebruikt64 targetshots; ZNE en beide L-MPF-varianten gebruiken43+7+14.
Alle gebruiken dezelfde128 kalibratieshots, dus192 per primaire estimator.
De oude extra-shotsvariant is niet in deze primaire vergelijking opgenomen.

| Absolute fout | Lading | Spin | Doublon |
| --- | ---: | ---: | ---: |
| Vorige L-MPF | 0.434140 | 0.350841 | 0.319159 |
| Shotafhankelijke L-MPF | 0.183210 | 0.165252 | 0.170993 |
| Daling in deze steekproef | 57.8% | 52.9% | 46.4% |

Dit zijn dalingen van de gerealiseerde puntfouten, niet bewezen dalingen van
de algemene bias of MSE. Tegen readout-only is de nieuwe spinpuntschatting
beter, maar lading en doublons niet. Tegen ZNE is de doublonpuntschatting iets
beter, maar lading en spin niet. Er is geen methode-per-observable geselecteerd
op basis van de bekende referentie.

## Wat is veranderd?

De oude straf ridge 1/56 behandelt alle drie armen gelijk. De nieuwe regel is,
voor iedere Pauli-operator en arm:

```text
v_a = (max_y score_a(y) - min_y score_a(y))^2 / 4
Lambda_aa = v_a / N_a,  N = (43,7,14)
minimize F00 - 2 b^T c + c^T G c + c^T Lambda c
subject to sum(c)=1.
```

De scores omvatten ALLE vier mogelijke centrale bituitkomsten na de bestaande
readoutinversie en het terugdraaien van het X-masker. De variantiegrens gebruikt
geen targetfrequenties, targetgemiddelden of exacte doelwaarden. Zo krijgen
onwaargenomen uitkomsten niet kunstmatig nulvariantie omdat er maar7 shots zijn.

De regel volgt uit Var(X)<=(max X-min X)^2/4. Delen door N geeft een grens voor
de variantie van een gemiddelde van onafhankelijke shots. De diagonale straf
begrenst de samplingvariantie van de combinatie, conditioneel op de kalibratie
en onafhankelijke armen. Hij begrenst niet de totale fout door modelbias,
kalibratiemisspecificatie, TN-truncatie of drift.

De sterkte is eenmaal vastgezet op eta=1, zonder scan of referentie-tuning.
De oude scalar ridge is vervangen, niet extra opgeteld. Deze keuze is een
heuristische bias/variantie-afweging: de genormaliseerde HS-projectieverliesfunctie
is niet hetzelfde als de echte toestandsspecifieke bias in het kwadraat.
Het nieuwe protocol is gekozen na de vorige mislukte pilot op dezelfde data;
dit is dus geen geblindeerde of onafhankelijke confirmatie.

| Operator | Straf factor1 | Straf factor2 | Straf factor3 |
| --- | ---: | ---: | ---: |
| Z_up / Z_down | 0.023988 | 0.147356 | 0.073678 |
| ZZ | 0.024744 | 0.151997 | 0.075999 |

| Operator | Nieuwe c1 | Nieuwe c2 | Nieuwe c3 |
| --- | ---: | ---: | ---: |
| Z_up | 1.790038 | -0.089572 | -0.700466 |
| Z_down | 1.582674 | -0.071706 | -0.510968 |
| ZZ | 1.912133 | -0.156298 | -0.755835 |

De som is telkens 1 binnen afronding. Niet ieder individueel gewicht hoeft
kleiner te worden; de armen zijn gekoppeld door G en de somconstraint.
De nieuwe low/high-chi coefficient-L1-veranderingen zijn
0.007331, 0.008231 en 0.018197, allemaal onder de bestaande 0.05-grens.
Er zijn geen nieuwe operator-TNs berekend.

## De afweging is zichtbaar, niet verborgen

| Operator | Projectieverlies oud -> nieuw | Samplingvariantiegrens oud -> nieuw |
| --- | --- | --- |
| Z_up | 0.139952 -> 0.205873 | 0.218584 -> 0.114197 |
| Z_down | 0.105386 -> 0.148745 | 0.148201 -> 0.080081 |
| ZZ | 0.243049 -> 0.364839 | 0.327163 -> 0.137600 |

De samplingvariantiegrens daalt, maar het model-projectieverlies stijgt.
De som van beide wordt voor iedere operator kleiner, zoals de optimizer
vereist. Deze objectiefwaarden zijn geen gemeten hardwarefouten.

## Onzekerheid inclusief kalibratieafhankelijke gewichten

Voor alle 10,000 eerder opgeslagen gepaarde replicaties zijn dezelfde targetcounts
en kalibratietrekkingen gebruikt. De nieuwe gewichten worden in iedere replicatie
uitsluitend via de kalibratietrekking en vaste G/b opnieuw bepaald. Ze worden
niet aan de targetmetingen of referentie aangepast. Dit propageert de nieuwe
kalibratieafhankelijkheid van de regularisatie. Een frozen-weight- en een
fixed-calibration-variant zijn daarnaast afzonderlijk opgeslagen.

| Bootstrap-SD, primaire behandeling | Lading | Spin | Doublon |
| --- | ---: | ---: | ---: |
| Vorige L-MPF | 0.278384 | 0.283376 | 0.174504 |
| Shotafhankelijke L-MPF | 0.192455 | 0.207963 | 0.103542 |
| Daling van de SD | 30.9% | 26.6% | 40.7% |

Gepaard 95%-percentielinterval voor absolute fout(baseline)-absolute fout(nieuw),
dus positief betekent verbetering:

| Tegen | Lading | Spin | Doublon |
| --- | --- | --- | --- |
| Readout-only | [-0.4764, 0.2482] | [-0.4175, 0.3749] | [-0.3515, 0.0531] |
| ZNE | [-0.1889, 0.1339] | [-0.2899, 0.2214] | [-0.0304, 0.0656] |
| Vorige L-MPF | [-0.1006, 0.4397] | [-0.1022, 0.3724] | [-0.000545, 0.297955] |

Alle negen intervallen omvatten 0. Vooral de onderste doublongrens tegen de oude
L-MPF mag niet naar een positieve waarde worden afgerond. Er is geen scan van
replicatieaantallen of seeds uitgevoerd om die grens te laten omslaan.

De intervallen behouden de beperkingen van de vorige pilot: heuristische
bootstrap/posterior-combinatie, geen gegarandeerde dekking bij slechts 7/14
gevouwen shots, en geen dekking van model-, TN-, drift- of gecorreleerde-readoutbias.

De nieuwe puntschatting blijft onfysisch: Zu=1.305812 en gereconstrueerde
kansen `[0.617232, 0.008401, 0.535674, -0.161307]`.
Negatieve waarden zijn niet afgeknipt; de positieve totale centrale lading
betekent dus niet dat de volledige lokale reconstructie fysisch geldig is.

## Verificatie, timing en behoud

- Alle 51 tests slagen: de eerdere 45 plus variantiegrens-, analytische limiet-,
  scalar-ridge-, afwijzings- en onafhankelijke solvercontroles.
- De onafhankelijke auditor reconstrueert de scores via een assignmentmatrix,
  en de gewichten via een direct KKT-stelsel in plaats van de productie-
  null-space-oplossing. Alle 10,000 replicaties en gepaarde intervallen zijn geaudit.
- Maximale puntgewichtsafwijking: 3.33e-16; maximale bootstrapgewichtsafwijking:
  2.00e-15; maximale fysieke bootstrapafwijking: 1.17e-15.
- De oude baselines, subsetindices en bootstrapdraws zijn ongewijzigd. Beide
  objectiefcomponenten, alle nieuwe gewichten/straffen en onzekerheidsvarianten
  zijn opgeslagen. Geen oorspronkelijke meetdata of mislukte resultaten verwijderd.
- Runfunctie 4.266 s, auditfunctie 1.295 s, exclusief imports/launcher, documentatie
  en Git. De eerdere TN-kosten blijven onderdeel van de totale voorbereiding.
  Geen nieuwe QPU-tijd en geen quantum-advantage- of end-to-end-snelheidsclaim.
- De twee NPZ-bestanden zijn 2,101,840 en 3,062,205 bytes, beide kleiner dan 10 MB.

## Conclusie en volgende stap

De physics-verificatieskill maakt het onderscheid expliciet: de nieuwe regel
vermindert hier de samplingversterking en de gerealiseerde puntfouten tegenover
de oude L-MPF, maar bewijst geen algemene hardwarewinst. Doublons blijven negatief
en readout/ZNE worden niet op alle grootheden overtuigend verslagen. Geen 6x6.

Verder tunen op deze ene twirl zou de kans op selectiebias vergroten.
Een volgende robuustheidscontrole hoort andere passende opgeslagen twirls of
controlemetingen te gebruiken. Daarvoor moeten de gewichten bij de werkelijke
circuits passen: nooit deze twirl0-coefficienten blind op een acht-twirlgemiddelde
toepassen. Eerst kan worden nagegaan of de bestaande operatorberekeningen
daar veilig voor herbruikbaar zijn. Dit vervolg is nog niet uitgevoerd.
Een nieuwe QPU-job vereist afzonderlijk, vers akkoord op backend en budget.

## Reproduceren

In de bestaande WSL-Qiskitomgeving, vanuit de repository, met een nieuwe map:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B lmpf_2d/shot_aware.py --output NEW_DIRECTORY
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B lmpf_2d/verify_shot_aware.py NEW_DIRECTORY
```

- [Plan en bronhashes](plan.json), [bevroren regel, gewichten en objectieven](frozen_rule_and_weights.json).
- [Volledige resultaten](summary.json), [hashmanifest](sha256.json).
- [Onafhankelijke audit](verification/verification.json), [verificatienotitie](VERIFICATION.md).
- [Vorige vaste-ridge pilot](../lmpf_3x3_central_hardware_2026-09-09_v1/DELIVERY.md).

Geen installatie, GitHub-push of publicatie.
