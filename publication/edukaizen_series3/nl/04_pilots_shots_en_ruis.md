---
part: 4
title: "Kleine pilots: ligt het aan shots of aan het circuit?"
slug: "hubbard-nighthawk-serie-3-04-pilots"
status: draft
language: nl
---
# Kleine pilots: ligt het aan shots of aan het circuit?

Een quantumuitkomst kan om verschillende redenen verkeerd zijn. Met te
weinig shots kan een schatting toevallig schommelen. Een te diep circuit
kan de bedoelde informatie systematisch verliezen. Een verkeerde mapping
kan zelfs op ideale hardware het verkeerde model uitvoeren. Meer shots
lost alleen het eerste probleem rechtstreeks op.

## Wat 512 shots wel en niet betekenen

Een shot is één uitvoering en meting van een circuit. Bij onafhankelijke
herhalingen neemt de gewone statistische standaardfout typisch af als
één gedeeld door de wortel uit het aantal shots. Vier keer zoveel shots
geven dan ongeveer een halvering van de standaardfout, niet vier keer
zoveel nauwkeurigheid.

In ons project is 512 vaak het aantal shots per instelling. Een job kan
meerdere tijdpunten, twirls, trainingscircuits en kalibraties bevatten.
De laatste gepaarde run had 76 PUBs van elk 512 shots: samen 38.912
metingen. 'Een run met 512 shots' beschrijft die totale job dus onvolledig.

Als ruis een spinprofiel bijna heeft uitgewist, kunnen extra shots juist
heel precies bevestigen dat het ruizige profiel bijna vlak is. Dan is
circuitverbetering of betrouwbare mitigatie nodig, niet alleen statistiek.

## Waarom eerst 3x3 en 5x5?

Op kleine roosters kunnen we meer exact controleren. We kunnen de
fermion-Hamiltoniaan in bezettingsruimte opbouwen, de ideale circuituitkomst
berekenen en de meetgrootheden site voor site vergelijken. Daarmee
onderscheiden we programmeerfouten van hardwareproblemen.

Een voorbereidende 5x5-controle maakt het mogelijk de toestandspreparatie
te vergelijken met een dynamisch circuit. Dat een voorbereidingscontrole
de juiste deeltjesaantallen geeft, betekent niet dat een lange evolutie die
kwaliteit behoudt. En een geslaagde niet-interagerende controle is nog geen
bewijs dat de interagerende U=8-target goed is.

## Aer als gerichte diagnose

Een ruissimulator met opgeslagen Nighthawk-parameters helpt specifieke
vragen te onderzoeken: hoeveel effect hebben readoutfouten, éénqubitruis
en CZ-ruis afzonderlijk? Wat verandert bij extra folding of meer shots?
Het voordeel is dat we dezelfde bedoelde schakeling ook zonder ruis kunnen
doorrekenen op de kleinere gevallen.

Zo'n simulator is geen volledige digitale tweeling van het apparaat.
Drift, gecorreleerde fouten en niet-gemodelleerde effecten kunnen ontbreken.
Een spinpiek in Aer is daarom een aanwijzing over het geteste ruismodel,
niet automatisch een verklaring van iedere hardwarepiek.

Ook random seeds vragen controle. Het archief bewaart een correctie voor
overlappende seeds: schijnbaar verschillende simulaties kunnen anders
statistisch afhankelijk zijn. Een eerlijke vergelijking bewaart zulke
correcties in plaats van alleen het aantrekkelijkste plaatje te tonen.

Bronnen: AER_NIGHTHAWK_512_PROTOCOL.md, AER_SEED_CORRECTION_2026-09-06.md,
HARDWARE_CONTROL_5X5_PROTOCOL.md en HARDWARE_COMPACT_TFLO_PROTOCOL.md.
