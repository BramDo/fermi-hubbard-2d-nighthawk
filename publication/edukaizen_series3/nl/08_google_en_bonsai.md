---
part: 8
title: "Hoe dicht zitten we bij Google en de Bonsai-resultaten?"
slug: "hubbard-nighthawk-serie-3-08-vergelijking"
status: draft
language: nl
---
# Hoe dicht zitten we bij Google en de Bonsai-resultaten?

Voor een klein project is het interessant om niet alleen naar de eigen
vorige run te kijken. Wat publiceren grotere onderzoeksgroepen voor
vergelijkbare roosters? De bruikbare vraag is niet wie het meest indrukwekkende
qubitgetal noemt, maar welke observabelen onder welke omstandigheden zijn
gemeten en hoe de referentie tot stand kwam.

## Google is vooral zichtbaar op 5x5, maar heeft ook 6x6-data

Veel uitvoerig besproken figuren in de Google/Phasecraft-publicatie gaan
over 5x5. Toch bevat de openbare dataset ook volledige lokale Z- en
ZZ-verwachtingswaarden voor 6x6. We hebben die data rechtstreeks gebruikt,
zonder punten uit afbeeldingen te schatten. Zie de
[paper](https://arxiv.org/abs/2510.26845v2) en
[de dataset](https://zenodo.org/records/17881822).

Onze selectie is beperkt: een holon-stripe-begintoestand, U=8, T=0,4,
nul flux en twee of drie Trotterlagen. Uit de Pauli-momenten berekenen we
dezelfde lading, spin en doublons als in onze eigen analyse. Googles
spindefinitie is hier al n_up-n_down; een extra factor twee zou fout zijn.

## De lokale afwijkingen in dezelfde eenheden

Iedere rij hieronder wordt vergeleken met zijn eigen modelreferentie.
Google gebruikt in deze vergelijking TDVP chi2048, wij de nog niet
geconvergeerde chi64. De waarden zijn RMS-afwijkingen over alle lokale sites.

| Gemitigeerd resultaat | Lading | Spin | Doublons |
|---|---:|---:|---:|
| Google 5x5, twee lagen | 0,01779 | 0,02280 | 0,01021 |
| Google 5x5, drie lagen | 0,02431 | 0,04269 | 0,01841 |
| Google 6x6, twee lagen | 0,02809 | 0,04478 | 0,02497 |
| Google 6x6, drie lagen | 0,02661 | 0,08023 | 0,02971 |
| Ons 6x6, origineel + TFLO | 0,08389 | 0,09185 | 0,05080 |
| Ons 6x6, compact + TFLO | 0,10930 | 0,12586 | 0,06412 |

Voor de geselecteerde 6x6-tweelaagsvergelijking zijn onze afwijkingen
ongeveer twee keer zo groot voor spin en doublons en drie keer voor
lading. Dat is dezelfde orde van grootte, niet dezelfde bewezen kwaliteit.
Onze Hamiltoniaan bevat diagonale hopping en onze toestand heeft N=32;
de geselecteerde Google 6x6-toestand heeft N=30 en t'=0.

Googles referentie is bij dit tijdpunt bovendien behoorlijk stabiel:
chi1024 naar chi2048 verandert het 6x6-spinprofiel met ongeveer 0,00021
RMS. Dat is geen strikt foutcertificaat, maar wel veel kleiner dan de
getoonde hardwareafwijkingen. De vergelijking is daarom inhoudelijker dan
de constatering dat beide projecten een 6x6-rooster noemen.

## Bonsai beantwoordt weer een andere vraag

De [heavy-hex-publicatie van Esposito en collega's](https://arxiv.org/abs/2608.25024)
combineert hardware-afhankelijke mapping en Hamiltoniaansimulatie tot 6x6.
De daar gebruikte Boston-processor is Heron r3, geen Nighthawk. Een mapping
die op dat verbindingspatroon goed werkt, moet op onze hardware opnieuw
worden beoordeeld. Een ander U, tijdpunt of integratieschema kan evenmin
door simpel normaliseren in onze doelopgave worden veranderd.

## Een eerlijke waardering

Deze vergelijking maakt ons resultaat niet waardeloos. Met beperkte
middelen hebben we een werkende 72-modusroute, een groot controlearchief
en gemitigeerde observabelen in een relevante orde van grootte. Het
verantwoorde vervolg is daarvan leren, niet alvast de titel 'beste 6x6'
opeisen. De volledige omzetting en haar metadatawaarschuwingen staan
onder google_conversion_2026-09-07_v1 in onze repository.
