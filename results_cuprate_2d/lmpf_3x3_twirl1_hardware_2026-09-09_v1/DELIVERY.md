# Twirl1 hardware: ladingpunt dichtbij exact, nog geen robuuste verbetering

De passende shot-aware L-MPF-gewichten zijn toegepast op de opgeslagen
twirl1-metingen. De centrale ladingpuntschatting ligt dicht bij de exacte
circuitreferentie. Spin en doublons wijken nog duidelijk af. Alle zes gepaarde
verbeteringsintervallen tegenover readout-only en ZNE bevatten nul.

Daarom: interessante puntschatting voor lading, maar GEEN gevalideerde algemene
hardwareverbetering en GEEN groen licht voor6x6.

## Centrale observabelen

Dit is slechts het centrale roosterpunt van3x3, niet het totale N en niet het
volledige ladings-/spinprofiel. Spin=n_up-n_down; D=lokale doublonkans.
De referentie is exact voor het eindige circuit, niet automatisch exp(-iHT).

| Methode | Centrale lading | Centrale spin | Centrale doublons |
|---|---:|---:|---:|
| Exacte circuitreferentie | 0.404671 | -0.362021 | 0.009685 |
| Ruw64, diagnostisch | 0.593750 | -0.062500 | 0.109375 |
| Readout-only64 | 0.587402 | -0.063477 | 0.108170 |
| Readout + lineaire ZNE | 0.447761 | -0.065234 | 0.188347 |
| Readout + shot-aware L-MPF | 0.413192 | -0.133000 | 0.125556 |

Absolute afwijkingen ten opzichte van dezelfde referentie:

| Methode | Lading | Spin | Doublons |
|---|---:|---:|---:|
| Readout-only | 0.182732 | 0.298545 | 0.098484 |
| ZNE | 0.043090 | 0.296787 | 0.178661 |
| L-MPF | 0.008521 | 0.229021 | 0.115871 |

L-MPF is in DEZE puntschattingen beter dan ZNE voor alle drie observabelen.
Tegenover readout-only zijn lading en spin dichterbij, maar doublons juist
iets verder van de referentie. De kleine ladingsafwijking is geen nauwkeurigheids-
certificaat: de samplingonzekerheid is veel groter.

## Onzekerheid, niet weg te laten

Gepaarde bootstrap-standaarddeviaties, met gedeelde readout-kalibratie en
kalibratie-afhankelijke L-MPF-gewichten:

| Methode | Lading SD | Spin SD | Doublons SD |
|---|---:|---:|---:|
| Readout-only | 0.087301 | 0.077926 | 0.039691 |
| ZNE | 0.215132 | 0.193102 | 0.111785 |
| L-MPF | 0.216146 | 0.202255 | 0.113570 |

Voor L-MPF zijn de heuristische95%-percentielintervallen:
lading[0.001564,0.845848], spin[-0.531675,0.264918],
doublons[-0.092233,0.352514]. Dit zijn geen gegarandeerde dekkingsintervallen,
vooral door slechts7 shots in de factor2-arm.

Verbetering = absolute fout baseline MINUS absolute fout L-MPF.
Positief betekent een kleinere L-MPF-fout. Alle onderstaande intervallen
bevatten nul; ook een verslechtering blijft mogelijk binnen deze analyse.

| Baseline | Observable | Puntverbetering | Heuristisch95%-interval |
|---|---|---:|---|
| Readout-only | lading | +0.174210 | [-0.349009,0.229498] |
| Readout-only | spin | +0.069524 | [-0.256014,0.278532] |
| Readout-only | doublons | -0.017386 | [-0.187856,0.082906] |
| ZNE | lading | +0.034569 | [-0.263435,0.275014] |
| ZNE | spin | +0.067766 | [-0.099424,0.220944] |
| ZNE | doublons | +0.062791 | [-0.093526,0.221389] |

Onbekende device-modelbias, tensortruncatiefout, drift en gecorreleerde readout
zijn niet door deze intervallen afgedekt. Meer shots kunnen samplingonzekerheid
verkleinen, maar zijn geen bewezen oplossing voor zulke systematische fouten.

## Fysieke plausibiliteit

De vier lokale L-MPF-puntschattingen voor kansen(00,10,01,11) zijn:
[0.712364,0.014540,0.147540,0.125556]. Ze zijn hier allemaal positief en
genormaliseerd. Er is niets afgeknipt of geprojecteerd. De bootstrap behoudt
ook negatieve schattingen, zoals zichtbaar in het doubloninterval.

Dit is geen bewijs van robuustheid over twirls. De eerdere twirl0-resultaten
met negatieve doublons blijven behouden; ze zijn andere steekproeven en
gebruiken hun eigen passende operatorcoefficienten.

## Gelijke shots en correcte bronnen

Archiefjob daem7r642tqs73autong op ibm_phoenix,3x3 Hubbard,18 actieve modi,
U8,T0.4,twee symmetrische circuitstappen, twirl1. Native records25/19/2
bij CZ-factoren1/2/3. Geen nieuwe QPU-run of remote retrieval.

- Readout-only gebruikt64 factor1-targetshots.
- ZNE en L-MPF gebruiken43/7/14 targetshots, ook totaal64.
- Alle drie delen128 kalibratieshots:192 archiefshots per estimator.
- Hun gezamenlijke data-unie is85 target plus128 kalibratie=213; geen nieuwe
  consumptie en niet213 onafhankelijke shots per methode.
- Ruw64 is alleen diagnostisch en gebruikt geen readout-kalibratie.
- Geen all85-L-MPF-variant in de primaire vergelijking.

Gewichten zijn uit de passende twirl1-Grams gehaald:
Z_up/Z_down chi128,ZZ chi256. De matrices, gewichten, subsetseed2026090917,
bootstrapseed2026090918 en10,000 herhalingen zijn vastgelegd voordat de
targetwaarden zijn gescoord. Geen referentiewaarden in de optimizer.

De numerieke exacte-normcontroles waren geslaagd; de ruwe ZZ-Gram-verandering
van1.31% bleef boven zijn1%-grens. Dat negatieve diagnostische resultaat is
niet gewijzigd. Dit is hergebruikte-data-robuustheid, geen geblindeerde holdout.

## Verificatie, tijd en vervolg

79 tests en de onafhankelijke controle zijn geslaagd. De auditor herhaalde
alle10,000 calibration/target-bootstrapdraws, reconstrueerde de readout-inversie
via een4x4 assignmentmatrix en loste de gewichten als KKT-stelsels op.
Maximale afwijking in fysieke waarden1.11e-15.

De procedure duurde26.26s, waarvan20.12s voor controle van operatorbestanden
en1.31s voor de data-analyse. Onafhankelijke audit3.06s; importopstart apart.
Geen nieuwe TN-propagatie. De eerder gemaakte klassieke operatorberekeningen
zijn EXTRA voorbereidingstijd en verdwijnen niet uit een end-to-end vergelijking.

De physics-verificatieskill heeft de gelijke shotbudgetten, referentievrije
fit, volledige onzekerheidspropagatie en het bewaren van ongunstige uitkomsten
bepaald. De heranalyse is opgeslagen; eerdere datasets zijn niet gewijzigd.

Volgende zinvolle diagnose: [voorspelt ons ruismodel de afzonderlijke armen?](NEXT_NOISE_MODEL_CHECK.md).
Dit kan met de al opgeslagen operatoren, zonder nieuwe grote berekeningen
of QPU. Het kan helpen onderscheiden waar sampling en modelafwijking spelen,
maar geeft niet automatisch toestemming om het model op dezelfde targetdata
te trainen of om naar6x6 op te schalen.
