---
part: 9
title: "Van een snelle run naar een betrouwbaar antwoord"
slug: "hubbard-nighthawk-serie-3-09-volgende-stap"
status: draft
language: nl
---
# Van een snelle run naar een betrouwbaar antwoord

De volgende stap is niet automatisch een groter rooster. Ons project
heeft al een interessante lokale tijdsverhouding en een volledige 6x6-route.
De belangrijkste open vraag is hoeveel betrouwbare U=8-informatie de
quantummeting na mitigatie werkelijk toevoegt.

## Eerst de estimator toetsen

We kiezen vooraf welke observabelen we willen schatten en welke afwijking
we acceptabel vinden. Lading, spin en doublons krijgen ieder een eigen
tolerantie. Een gemiddelde over alle soorten observabelen kan anders een
slechte spinschatting verbergen achter een eenvoudigere ladingcontrole.

Daarna testen we de mitigatie op instellingen waarvan we het antwoord
wel kennen, maar die niet in de training zitten. Onze laatste U=0-holdouts
laten zien dat dit nog werk vraagt. Als de methode zelfs daar niet goed
generaliseert, is een mooie U=8-targetwaarde onvoldoende onderbouwing.

De controle zonder targethardware-input blijft daarbij belangrijk.
Wanneer een schatter ongeveer hetzelfde antwoord geeft zonder de
interagerende hardwaredata te gebruiken, meet dat antwoord niet overtuigend
de gewenste quantumdynamica. We willen juist aantonen dat die data nuttige,
controleerbare informatie toevoegen.

## Twee ladders, niet één

Aan de klassieke kant verfijnen we de bond-dimensie. Aan de quantum- en
circuitkant moeten we ruis, herhalingen en tijdstapfout onderscheiden.
Meer chi verhelpt geen verkeerd circuit; meer shots verhelpt geen
verkeerde fermionmapping; betere readout verhelpt niet iedere poortfout.

Een bruikbare opzet houdt T vast, vergelijkt meerdere tijdstappen en gebruikt
steeds de juiste referentie voor het gekozen eindige circuit. Pas daarna
kan de afwijking van de continue Hamiltoniaandynamica worden beoordeeld.
Bij een kostenlimiet is het verstandiger één duidelijke vraag te toetsen
dan veel factoren tegelijk te veranderen.

## De sterkere snelheidsproef

De circa 20x-verhouding uit deze serie gebruikt geregistreerde QPU-tijd
en de bestaande lokale klassieke rekenkerntijd. Voor een sterkere proef
leggen we ook voorbereiding, training, kalibratie, wachttijd en analyse
vast. We maken expliciet of een kalibratie eenmalig is of over meerdere
berekeningen wordt hergebruikt.

De finishlijn is dan niet 'de job is klaar', maar 'de gevraagde observabelen
halen de afgesproken fouttolerantie'. Daarmee kunnen we een echte
time-to-acceptable-answer-vergelijking maken voor onze lokale computer.
Dat is nog steeds een beperkte, haalbare doelstelling; zij vereist niet
dat we iedere klassieke computer ter wereld verslaan.

## Een dossier dat een ander kan controleren

De aparte Nighthawk-repository bewaart code, theorie, ruwe metingen,
kalibraties, referenties, controlesommen en de resultaten van minder
succesvolle routes. Grote bestanden zijn verliesvrij gecomprimeerd en
hebben een herstelmanifest. De oorspronkelijke projectmap blijft bestaan.

Deze serie is daarom geen eindverklaring, maar een goed gedocumenteerd
tussenresultaat. We mogen trots zijn op wat met een beperkt budget is
bereikt én precies blijven over wat nog niet bewezen is. De volgende
hardwarejob wordt pas ingediend na een nieuwe expliciete budgettoestemming.

Bronnen: theory/RESULTS_AND_CLAIMS.md, HARDWARE_COMPACT_TFLO_PROTOCOL.md,
de holdouttabellen en de bewaarde chi32/chi64-controles in de projectrepo.
