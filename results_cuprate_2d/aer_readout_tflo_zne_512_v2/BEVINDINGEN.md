# Combineren helpt hier ZNE, maar voegt vrijwel niets toe aan TFLO

Lokale Aer-pilot voltooid, geen nieuwe QPU-seconden. Zelfde3x3 Hubbard,
U/t=8,T=0.4,twee Trotterstappen,18 modes en opgeslagen Nighthawk-layout/ruis.
Elke hoofdarm heeft512 shots inclusief kalibratie/training. Dit is geen
hardwarevergelijking en niet hetzelfde postselectie+TFLO-protocol als eerder.

| Hoofdarm | Lading-RMSE | Spin-RMSE | Doublon-RMSE |
|---|---:|---:|---:|
| Raw | 0.08444 | 0.24186 | 0.08807 |
| Readout-correctie | 0.08702 | 0.22609 | 0.08592 |
| Readout + TFLO | 0.03620 | 0.20508 | 0.05745 |
| Readout + lineaire ZNE | 0.08983 | 0.16482 | 0.08704 |

Kleiner is beter. TFLO heeft de beste centrale lading-/doublonwaarden;
ZNE de beste centrale spinwaarde. Geen algemene winnaar uit deze pilot.

## Wat voegt readout-correctie zelf toe?

Op identieke geselecteerde ZNE-bitstrings gaat spin-RMSE van0.18322 naar0.16482
(ongeveer10.0% lager). Het hybride95%-interval voor de absolute verbetering
is[0.00764,0.02437]. Lading/doublon hebben geen duidelijk opgeloste extra winst.
Bij TFLO gaat spin-RMSE van0.205067 naar0.205080: praktisch geen verschil.
Het interval voor de TFLO-readouttoevoeging omvat nul voor alle drie observabelen.
Deze zonder-readout controles zijn gepaarde diagnostiek op dezelfde data,
geen apart voor hun vrijgekomen128 kalibratieshots geoptimaliseerde armen.

Primair verschil spin-RMSE(ZNE)-spin-RMSE(TFLO)=-0.04026,
hybride95%-onzekerheidsinterval[-0.08407,0.02406]. De spinrangorde is dus
niet duidelijk opgelost. Vaste-kalibratiebootstrap geeft[-0.08403,0.02329].
De200/1000/2000-replicatiechecks veranderen deze conclusie niet.
Dit zijn bootstrap+Jeffreys-kalibratieposteriorintervallen, geen bewezen
frequentistische95%-dekking en geen onzekerheid over alle systeemfouten.

De vrijwel gelijke TFLO-uitkomsten zijn verenigbaar met de affine structuur:
voor de enkelvoudige Z-momenten is readoutcorrectie bij dezelfde acht maskers
een vaste affine transformatie van de ingang; een opnieuw geleerde affine
TFLO-fit kan die grotendeels opvangen. Zwakke ridge en ZZ-momenten doorbreken
exacte invariantie. Dit is een verklaring voor deze implementatie, niet een
bewijs dat readoutcorrectie bij iedere TFLO-variant overbodig is.

## Klassieke controle en fysieke grenzen

De zuiver klassieke U0-FLO-voorspelling heeft RMSE[0.03775,0.21556,0.07454].
Voor spin is TFLO niet aantoonbaar beter binnen het gebruikte interval:
klassiek-minus-TFLO[-0.00735,0.02123]. Over alle27 Pauli-momenten is de MSE
wel lager:0.053862 versus0.066256, hybride verbetering[0.00447,0.01621].
Dat is alleen een exploratief Aer-resultaat bij dit kleine simuleerbare circuit,
geen vervanging voor een sterke klassieke dynamica-baseline of quantum advantage.
Geen van de centrale methodeschattingen heeft negatieve lokale paar-
waarschijnlijkheden of Pauliwaarden buiten[-1,1]; er is niets geclipt.

## Kosten en beperkingen

Raw:512 doelshots. Readout-only:384 doelshots+128 kalibratie.
TFLO:192 doelshots+192 training (zesmaal32)+128 kalibratie.
ZNE:216/56/112 doelshots op ruisfactor1/2/3+128 kalibratie.
Kalibratie:64 shots voor elk van all-zero/all-one; volledige Aer-ruis,
dus inclusief X-preparatiefout bij all-one. Onafhankelijke uitleesfouten
worden aangenomen. De correctie is lokale inverse-momentcorrectie, geen M3/TREX.

ZNE gebruikt669312 CZ-toepassingen, TFLO387072, raw516096. Gelijke shots
betekenen geen gelijk CZ-, werkelijk looptijd- of facturatiebudget.
Nieuwe bemonstering:320 Aer-shots. Runner465.49s inclusief exacte controles
en archivering; geen end-to-end timingvergelijking tussen methoden.
Of een hardwarepakket inclusief kalibratie binnen5s past is niet vastgesteld.

U8-doeldata zijn hergebruikt uit de eerder bekeken pilot. Dit is daarom
retrospectief/verkennend. U0-training en kalibratie zijn nieuw en seed-disjunct.
TFLO gebruikt geen U8-referentie in de fit en geen postselectie in deze proef.
Vier trainingsshots per twirl zijn te weinig voor een convergentieclaim.
Intervallen omvatten geen model-/extrapolatie-/TFLO-transferbias, hardwaredrift
of systematische kalibratie-preparatiefout. Met de exact bekende ruismatrix
(alleen oracle-diagnose) is ZNE-spin-RMSE0.17243; kalibratie is geen gratis
perfect gekend model en een toevallig betere puntschatting is geen bewijs.

## Verificatie en volgende beslisstap

58 unit-/regressietests geslaagd. Alle48 trainings-QPY's ruisvrij gecontroleerd:
maximale referentieafwijking2.00e-13. Reconstructie van het opgeslagen ruismodel
wijkt maximaal1.78e-15 af;18 readoutkanalen identiek. Onafhankelijke directe
bitweging met2x2-matrixinversies, eigen ridge-normalvergelijkingen en een OLS-fit
reproduceert alle methoden tot6.11e-15.131 ouderbestanden zijn hash-gecontroleerd.
De mislukte v1-loaderpoging blijft bewaard; daarin waren nul shots uitgevoerd.

De volgende zinvolle stap is een onafhankelijke, vooraf vastgelegde herhaling
met verse doelshots en voldoende TFLO-training, met expliciete shot- EN
poort-/tijdkosten. Postselectie of TFLO+ZNE stapelen is nog niet getest en mag
niet als bewezen verbetering worden gepresenteerd. Geen nieuwe QPU-run gestart.

Bronnen: [TFLO-principe](https://arxiv.org/abs/2102.02120),
[measurement-mitigationcontext](https://qiskit.github.io/qiskit-addon-mthree/).
