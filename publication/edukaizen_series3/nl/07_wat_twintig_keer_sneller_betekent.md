---
part: 7
title: "Circa 20x: onze lokale snelheidsmijlpaal precies uitgelegd"
slug: "hubbard-nighthawk-serie-3-07-snelheid"
status: draft
language: nl
---
# Circa 20x: onze lokale snelheidsmijlpaal precies uitgelegd

Ons eigen snelheidsdoel verdient een eigen meetlat. Niet: is hiermee iedere
klassieke methode verslagen? Wel: hoeveel geregistreerde QPU-tijd gebruiken
we ten opzichte van de rekenkern van onze huidige lokale klassieke aanpak?
Met de opgeslagen metingen is dat een verhouding van ongeveer twintig.

## Twee afzonderlijke quantumjobs, één bestaande baseline

De chi64-rekenkern van de klassieke 6x6-baseline duurde 150,819180 seconden.
De koude worker inclusief imports duurde 156,905497 seconden, exclusief de
Windows/WSL-launcher. Er liep tegelijk ander lokaal werk; dit was dus geen
geïsoleerde prestatietest van het systeem.

Twee afzonderlijke quantumjobs registreerden respectievelijk 8 en 7 seconden
QPU-gebruik. De tweede bevatte zowel origineel als compact. Het is niet
correct beide jobs op te tellen en het resultaat als één noodzakelijk
quantumbudget te presenteren, of zeven seconden aan elke arm toe te kennen.

| Vergelijking | Berekening | Verhouding |
|---|---:|---:|
| Klassieke kernel / eerdere QPU-job | 150,819180 / 8 | 18,85x |
| Klassieke kernel / laatste gepaarde QPU-job | 150,819180 / 7 | 21,55x |

De compacte omschrijving is daarom circa 20x minder geregistreerde QPU-tijd
dan de klassieke rekenkerntijd van onze huidige baseline. Het is een
resourcevergelijking met expliciete klokken.

## Waarom het geen stopwatchvergelijking is

De nieuwste hardwarejob liep volgens de provider-tijdstempels ongeveer
181 seconden tussen running en finished. Alleen dat interval was al veel
langer dan de zeven geregistreerde QPU-seconden; wachtrij en lokale analyse
zijn daarmee nog niet volledig beschreven. De boekhoudkundige QPU-tijd en
de ervaren doorlooptijd beantwoorden dus andere vragen.

De [IBM-documentatie over workload usage](https://quantum.cloud.ibm.com/docs/en/guides/estimate-job-run-time)
is hier belangrijk: gebruik de providerregistratie zoals bedoeld en geef
er niet achteraf de betekenis van een volledige eindgebruikerstijd aan.

## En als chi64 nog niet genoeg is?

Een hogere bond-dimensie kan de klassieke berekening duurder maken.
Maar we hebben chi128 niet uitgevoerd. We mogen een geschatte langere
klassieke tijd dus niet alvast als extra gemeten quantumwinst boeken.
Omgekeerd kunnen verbeterde klassieke algoritmen of een andere observabele
de lokale berekening juist goedkoper maken.

Onze referentie is een MPS-benadering van het gekozen eindige circuit.
Zijn nauwkeurigheid moet afzonderlijk worden vastgesteld. Hetzelfde geldt
voor de quantumestimator, waarvan de TFLO-holdouts nog niet slaagden.
Een matched-accuracy-test kan pas een sterkere uitspraak doen als beide
kanten aan dezelfde vooraf gekozen fouttoleranties voldoen.

## Waarom deze beperkte mijlpaal toch telt

Het is zinvol om als klein project een concrete lokale tegenstander te
kiezen. De verhouding laat zien dat de geregistreerde QPU-resource voor
deze proef klein is ten opzichte van onze huidige klassieke rekenkern.
Dat motiveert verdere verbetering. De nauwkeurigheidscontrole neemt die
mijlpaal niet weg; zij bepaalt welke volgende claim verantwoord wordt.

Bronnen: beide provider_metrics.json-bestanden en summary.json van
classical_full_6x6_mps_T04_chi64_v1, integraal bewaard in de repository.
