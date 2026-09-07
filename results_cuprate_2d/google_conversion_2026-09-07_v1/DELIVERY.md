# Google-data omgerekend naar onze Hubbard-observabelen

7 september 2026. Volledige vergelijking: `report.html`; reproduceerbare
controle: `google_conversion_audit.ipynb`; alle profielen: `comparison.json`.

De nadruk in de paper ligt vaak op 5x5; de openbare dataset bevat ook lokale
6x6-profielen. We hebben vier vooraf gemotiveerde gevallen gelezen: holon
stripe, U=8, T=0.4, nul flux, 5x5 en 6x6, twee en drie Trotterlagen. Dit is
geen inventarisatie van alle resultaten of optimalisatie van een ranglijst.

Gemeten/afgeleide waarden na gepubliceerde Google-mitigatie of onze TFLO:

| Configuratie | N / N-doel | D per site | Spinprofiel-RMS | RMS lading | RMS spin | RMS doublons |
|---|---:|---:|---:|---:|---:|---:|
| Google 5x5, 2 lagen | 20.139 / 20 | 0.06663 | 0.60307 | 0.01779 | 0.02280 | 0.01021 |
| Google 5x5, 3 lagen | 20.260 / 20 | 0.07788 | 0.55372 | 0.02431 | 0.04269 | 0.01841 |
| Google 6x6, 2 lagen | 30.509 / 30 | 0.08966 | 0.56410 | 0.02809 | 0.04478 | 0.02497 |
| Google 6x6, 3 lagen | 30.443 / 30 | 0.09646 | 0.51646 | 0.02661 | 0.08023 | 0.02971 |
| Ons 6x6 origineel | 31.396 / 32 | 0.09013 | 0.65683 | 0.08389 | 0.09185 | 0.05080 |
| Ons 6x6 compact | 31.231 / 32 | 0.07719 | 0.67128 | 0.10930 | 0.12586 | 0.06412 |

De laatste drie kolommen zijn afwijkingen tegen ELK EIGEN modelreferentie,
geen bekende absolute fouten en geen matched-problem ranglijst. Google:
TDVP chi2048; ons: niet-geconvergeerde chi64 voor het eindige circuit.
Googles t-prime=0 en N20/30 verschillen van onze t-prime=-0.25 en N32.
Onze gemiddelde D is relatief dichtbij onze referentie, maar de lokale
profielen liggen verder weg. Google 6x6 is hier dus niet zonder kwantitatief
vergelijkingsmateriaal. Een winnaar- of voordeelclaim volgt hier niet uit.

## Definities en herkomst

charge=1-(Zup+Zdown)/2; spin=(Zdown-Zup)/2;
D=(1-Zup-Zdown+ZZupdown)/4. Google Eq. B1 gebruikt reeds nup-ndown:
geen extra factor twee. Gemiddelde D is per site; spinprofiel-RMS is de
grootte van het profiel, niet de afwijking. Geen clipping, N-vervanging of
tijdsinterpolatie. Elke RMS gebruikt alle 25 of 36 lokale sites.

Bronnen: https://arxiv.org/html/2510.26845v2 en
https://zenodo.org/records/17881822 . Exacte ZIP-paden, CRCs, SHA256s,
HTTP206 Content-Range en downloadomvang staan in de fetchmanifesten.
Niet de volledige 8.8GB ZIP gedownload. Vier originele HDF5-bestanden blijven
behouden; vier byte-exact herstelbare gzip-kopieen zijn ook bewaard.

Het losse initial_states.json herhaalt dezelfde configuratie voor
verschillende geometrieen/toestanden en is hiervoor onbruikbaar. HDF5
metadata en t=0-profielen tonen onafhankelijk de rij gaten en N20/30.
Die t=0-ankers zijn geen rauwe hardwaremetingen. Dit metadata-exportprobleem
is geen bewijs van verkeerde experimentele meetdata.

De 5x5-tweelaagsmap bevat geen TDVP-groep. Zijn vergelijking gebruikt
expliciet de passende continue-tijdreferentie uit de drielaagsmap. Voor
6x6 zijn de TDVP-profielen in beide mappen identiek gecontroleerd.
Chi1024->2048 RMS (lading/spin/D): 5x5 4.18e-6/1.42e-5/8.61e-6;
6x6 2.81e-5/2.13e-4/7.67e-5. Dit is een convergentie-indicator,
geen strikt certificaat. Marginale foutbalken missen de covariantie die
nodig is voor betrouwbare samengestelde foutbalken.

## Verificatie en rapportoppervlak

8 unittests geslaagd; notebook alle drie codecellen uitgevoerd; herlezing
van HDF5 reproduceert het gearchiveerde vergelijkingsresultaat exact.
Onafhankelijke vier-kansen-inversie en RMS-som gecontroleerd.
SQLite-herberekening van 14 rijen wijkt maximaal 7.11e-15 af.
Onze eerdere TFLO-holdout blijft mislukt; geen nieuwe validatieclaim.
Geen nieuwe QPU-job, klassieke dynamicasimulatie of publicatie.

MCP-rapportvalidatie en render-aanroep geaccepteerd, maar deze Codex-runtime
gaf geen inspecteerbare rapportlink of visueel verifieerbare output. Daarom
is het definitieve leveringsoppervlak het lokale, zelf-contained report.html,
gemaakt uit hetzelfde artifact.json door de canonieke rapportbouwer.
HTML-structuur en exacte payload gevalideerd. Geen compatibele Chromium
headless-shell beschikbaar: visuele/browser-QA, broninteractie en mobiele
lay-out zijn NIET geverifieerd. Er is geen browser geinstalleerd.

Notebook en brondata zijn de numerieke audit; de HTML is de leesweergave.
