# Uitkomst van de lokale vervolgstap

**Uitgevoerd zonder nieuwe hardwarejob: 0 extra QPU-seconden.** De twee
eerdere indieningslocks, ruwe bits, protocollen en primaire analyses zijn
ongewijzigd. Dit is een afzonderlijke verkennende audit van al bekeken data.

## De huidige TFLO-fit levert geen aantoonbare extra U=8-informatie

| Model | U=0-validatiefout (MSE) | U=8-doelfout (MSE) |
|---|---:|---:|
| Huidige TFLO met tijdterm | 0.002336 | 0.033645 |
| TFLO zonder tijdterm | 0.059559 | 0.074497 |
| Volledig klassiek model met alleen een U=0-tijdcurve | 0.002344 | 0.031355 |

De tijdcurvecontrole gebruikt geen gemeten quantumwaarden: zij wordt alleen
op de zes ideale U=0-referenties getraind. Haar puntschatting is op deze U=8-
doelen zelfs iets beter dan de huidige TFLO. Haar verwaarloosbare
bootstrapspreiding is geen bewijs van algemene juistheid: ze is simpelweg
deterministisch en bevat geen shotruis.

Ook als de U=8-meetwaarden in de huidige TFLO worden vervangen door de
U=0-meetwaarden op dezelfde tijden, wordt de MSE niet slechter als
puntschatting: 0.033037 versus 0.033645. Het gepaarde 95%-interval voor de
winst van echte U=8-input is [-0.007416, 0.003804] en bevat nul.

De projectie van het gecorrigeerde U=8-minus-U=0-contrast op het exacte
contrast is 0.0279, met interval [-0.0511, 0.1019]. Dit is een beschrijvende
schaalfactor, geen percentage quantumfidelity of bewijs dat er helemaal
geen interactiesignaal in de hardwaredata zit. De U=0-contrastpartners waren
trainingspunten. Een onafhankelijke overdrachtstoets vereist nieuwe data.

Conclusie: goede globale foutreductie is hier geen voldoende bewijs dat de
fit de interactiedynamica herstelt. De tijdterm simpelweg schrappen helpt
niet. Dit zegt iets over onze huidige vereenvoudigde kalibratie/fit, niet
dat TFLO als algemene methode niet kan werken.

## Geen betere route gevonden binnen de geteste klasse

De bestaande parallelle netwerkroute blijft de beste van vijf exact
equivalente routes: 1008 CZ en twee-qubitdiepte 144. De alternatieven hebben
1032, 1040, 1412 of 1624 CZ en meer diepte. Er is dus geen nieuwe
gatebesparing om als hardwareverbetering te claimen. Dit is geen bewijs
dat de bestaande route wereldwijd optimaal is.

De routetabel in het volledige verslag betreft ongetwirlde native circuits
met eindmetingen. De acht getwirlde/opgeschoonde templates zijn apart
gecontroleerd; deze blijven bij de oorspronkelijke beste netwerkroute.
De tijdsramingen gebruiken een opgeslagen kalibratie, geen live provider-
controle. De maximale gecontroleerde 18-qubit-toestandsafwijking is 1.10e-13.

## De Trotterfout is gecontroleerd, maar niet het grootste probleem

Voor U=8 zijn de spin-RMSE's tegenover exacte continue H-dynamica:

| Tijd | 2 stappen | 4 stappen | 8 stappen |
|---|---:|---:|---:|
| 0.2 | 0.005835 | 0.001420 | 0.000353 |
| 0.4 | 0.038274 | 0.008356 | 0.002020 |

De circa viervoudige daling bij verdubbeling van het aantal stappen bevestigt
de verwachte tweede-ordeconvergentie. De bestaande hardware-/mitigatiefout
tegenover het tweestapscircuit is groter: spin-RMSE 0.0869 en 0.2051.
Rechtstreeks tegenover exacte H wordt die 0.0924 en 0.2422. Deze fouten zijn
niet via een onterechte statistische kwadratuursom opgeteld.

Meer Trotterstappen verkleinen de discretisatiefout, maar betekenen ook meer
hardwaregates. Deze audit bewijst geen netto hardwarewinst door die verhoging.

## Aanbevolen volgende stap: eerst lokaal een beter kalibratieontwerp

Ontwerp U=0-training met meer onafhankelijke variatie dan alleen de tijd:
bijvoorbeeld meerdere bezettingspatronen bij een of twee vaste tijden,
steeds met N_up=N_down=4 en dezelfde dynamische circuitstructuur/diepte.
Zo kan worden getest of de ruiscorrectie identificeerbaar wordt zonder
dat een tijdcurve de gemeten verwachtingen vervangt.

Toets dit eerst lokaal in expliciet gelabelde ruismodellen en houd andere
U=0-instellingen en U=8-doelen buiten de training. Meet ook het U=8-minus-
U=0-contrast; een lage globale MSE alleen is onvoldoende. Dit is een
voorstel, geen al bewezen oplossing of toestemming voor een nieuwe QPU-job.

## Verificatie en volledige gegevens

- 20 regressietests geslaagd, waaronder volledige 2x2-operatorvergelijkingen
  met een onafhankelijke implementatie van de fermionische pariteitstekens.
- Alle vijf routes gecontroleerd op drie volledige 18-qubittoestanden;
  acht getwirlde/readout-gecorrigeerde templates en 80 bindings gecontroleerd.
- 32 Hamiltonian-, norm-, sector-, FLO- en referentiecontroles geslaagd.
- 14 aanvullende samenvattings-/reproductiecontroles geslaagd; 400 van 400
  bootstrapreplicaties bruikbaar. Broncode en resultaatbestanden zijn gehasht.

Volledig verslag: `summary/AUDIT_REPORT.md`. Modellen en bootstrapdata:
`transfer/`. Circuits: `circuits/`. Exacte Hamiltonianen, toestanden en
Trotterconvergentie: `trotter/`. Er is geen methode stilzwijgend tot nieuw
primair resultaat gepromoveerd en er wordt geen quantum advantage geclaimd.

[2D-paper: TFLO-overdracht en onafhankelijke controles](https://arxiv.org/html/2510.26845v2).
