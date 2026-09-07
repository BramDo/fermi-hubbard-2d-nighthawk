---
part: 5
title: "Readout, ZNE, PEC en TFLO: wat hebben we werkelijk gebruikt?"
slug: "hubbard-nighthawk-serie-3-05-mitigatie"
status: draft
language: nl
---
# Readout, ZNE, PEC en TFLO: wat hebben we werkelijk gebruikt?

Foutmitigatie kan gemeten observabelen sterk verbeteren. Maar 'mitigatie
aan' is geen enkele, universele schakelaar. Verschillende methoden richten
zich op verschillende fouten en gebruiken verschillende extra informatie.
In dit project hebben we meerdere routes onderzocht; ze mogen niet als één
grote combinatie op de laatste hardwaretabel worden geplakt.

## Readout: de meting kalibreren

Een qubit die als nul wordt voorbereid, kan soms als één worden gelezen,
en andersom. Met bekende voorbereidende toestanden schatten we een
verwarringsmatrix. Readout-mitigatie corrigeert vervolgens de gemeten
verdeling of de relevante momenten volgens dat kalibratiemodel.

Dat helpt bij meetfouten. Het kan niet zonder meer informatie herstellen
die eerder tijdens duizenden poorten verloren ging. Een te eenvoudig
readoutmodel kan bovendien gecorreleerde fouten missen.

## ZNE en PEC: ruis vergroten of statistisch compenseren

Zero-noise extrapolation, ZNE, vergelijkt uitvoeringen met verschillende
ruisniveaus en extrapoleert naar nul ruis. Bij CZ-folding vervangen we een
CZ bijvoorbeeld door drie CZ-poorten. Omdat CZ kwadraat de identiteit is,
blijft de ideale bewerking gelijk. De extra fysieke poorten vergroten wel
de blootstelling aan ruis, mits een optimizer ze niet weer verwijdert.

Probabilistic error cancellation, PEC, combineert ruizige bewerkingen met
getekende quasi-kansgewichten. De kwaliteit hangt af van het ruismodel;
de benodigde aantallen samples kunnen sterk toenemen. Beide methoden
vragen dus meer dan alleen het kiezen van een naam in een instellingenmenu.
Zie [Temme, Bravyi en Gambetta](https://arxiv.org/abs/1612.02058).

## TFLO: leren van een oplosbare buuropgave

Training with Fermionic Linear Optics gebruikt circuits die klassiek
efficiënt oplosbaar zijn. In onze toepassing nemen we U=0-trainingscircuits
en leren we het verband tussen hun exacte en ruizige Pauli-momenten.
Die correctie wordt daarna op de U=8-target toegepast. De aanpak is
geïnspireerd door [Montanaro en Stanisic](https://arxiv.org/abs/2102.02120).

De laatste gepaarde proef gebruikte per arm zes trainingsmomenten:
0,04; 0,08; 0,12; 0,24; 0,32; 0,48. Twee andere U=0-momenten, 0,2 en
0,4, dienden als holdouts. De U=8-target bij 0,4 leverde geen juiste
referentiewaarde aan de fit. De affine correctie werd apart per Pauli en
per circuitarm geleerd, met een kleine regularisatie naar de identiteit.

Dat is een controleerbare opzet, maar de holdouts slaagden niet voor onze
gekozen nauwkeurigheidseisen. Ook een controle zonder targethardware-input
kwam voor sommige grootheden dichter bij de chi64-referentie. Dan kan een
mooi TFLO-resultaat niet uitsluitend aan de gemeten U=8-dynamica worden
toegeschreven. De training draagt zelf veel informatie.

## Het label op de laatste run

De nieuwste original/compact-vergelijking gebruikte readoutcorrectie en
TFLO. ZNE, PEC, postselectie en DD waren daar niet ingeschakeld. Een
afzonderlijke eerdere DD-proef staat met een ander job-ID in het archief.

Onze gemitigeerde schattingen zijn veel interessanter dan de bijna vlakke
ruwe spinprofielen, maar blijven niet-gevalideerde schattingen. Negatieve
gereconstrueerde lokale kansen en mislukte holdouts worden daarom zichtbaar
gerapporteerd. Dat maakt verbetering gericht mogelijk.

Bronnen: HARDWARE_COMPACT_TFLO_PROTOCOL.md, TFLO_DD_6X6_PROTOCOL.md en de
bijbehorende ruwe data, fits, holdouts en ablaties in de projectrepo.
