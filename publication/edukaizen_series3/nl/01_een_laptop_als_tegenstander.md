---
part: 1
title: "Een laptop als tegenstander: ons Nighthawk-project"
slug: "hubbard-nighthawk-serie-3-01-laptop"
status: draft
language: nl
---
# Een laptop als tegenstander: ons Nighthawk-project

Ons doel begint niet bij het verslaan van iedere supercomputer. Het begint
bij een veel persoonlijkere vraag: kunnen wij als student-/hobbyproject een
quantumcomputer een interessante berekening laten uitvoeren met minder
geregistreerde rekentijd dan onze eigen klassieke computer nodig heeft?

Dat beperkte doel is de rode draad van deze derde Hubbard-serie. In de
eerste serie verkenden we het eendimensionale model. In de tweede stapten
we over naar twee dimensies. Nu concentreren we ons op IBM Nighthawk,
fysisch correctere fermioncircuits en een meetbare lokale tijdsvergelijking.

## De eerste mijlpaal: ongeveer twintig keer

Voor onze opgeslagen 6x6-opgave duurde de klassieke chi64-berekening
150,819 seconden in de rekenkern. Een Nighthawk-job registreerde 8 seconden
QPU-gebruik; een latere gepaarde original/compact-job 7 seconden. De
verhoudingen zijn ongeveer 18,85 en 21,55. Afgerond noemen we dat circa 20x.

Die verhouding is echt een uitkomst van de opgeslagen tijdregistraties.
Maar zij beantwoordt een specifieke vraag. QPU-gebruik is niet hetzelfde
als de tijd tussen op 'start' klikken en een gevalideerd antwoord lezen.
Wachtrij, voorbereiding, netwerkverkeer en lokale analyse staan niet allemaal
op die QPU-klok. Onze klassieke referentie is bovendien nog niet aangetoond
convergent: chi64 is een berekeningsinstelling, geen garantie op juistheid.

Daarom luidt onze claim: de quantumjob gebruikte circa twintig keer minder
geregistreerde QPU-tijd dan de rekenkern van onze huidige lokale klassieke
baseline. We claimen nog geen twintig keer kortere totale doorlooptijd bij
bewezen gelijke nauwkeurigheid.

## Wat rekent de quantumcomputer eigenlijk uit?

We simuleren een vereenvoudigd model van bewegende en onderling afstotende
elektronen: het tweedimensionale Fermi-Hubbard-model. Het rooster heeft
36 sites. Met twee spinmodi per site zijn dat 72 fermionmodi, weergegeven
op 72 qubits. De toestand bevat 32 deeltjes, niet 72.

We lezen niet de volledige quantumtoestand uit. We vragen naar lokale
lading, spin en dubbelbezetting. Zulke observabelen vertellen waar de
deeltjes zitten en hoe de gekozen begintoestand zich ontwikkelt. Een
bruikbare quantumrun moet op die gevraagde grootheden worden beoordeeld.

## Werken met een beperkt budget

De hardwareproeven groeiden van kleine pilots naar 6x6. We werkten met
512 shots per instelling en expliciete QPU-tijdgrenzen, uiteindelijk een
maximum van 15 seconden voor een toegestane job. Meer instellingen, extra
mitigatiecircuits en meer shots kosten samen budget. Er is dus geen gratis
combinatie van maximale diepte, veel tijdpunten en perfecte statistiek.

Dat maakt dit project leerzaam. We moesten beslissen welke controle het
meeste informatie oplevert, wanneer een circuit te diep wordt en wanneer
een mooi gecorrigeerd getal vooral iets over de correctiemethode zegt.

De [nieuwe repository](https://github.com/BramDo/fermi-hubbard-2d-nighthawk)
bevat daarom niet alleen aantrekkelijke eindtabellen. Ook broncode,
ruwe data, mislukte pilots en theorie blijven bewaard. Zolang de repo
privé is, is toegang alleen mogelijk voor gemachtigde lezers.

Bronnen: de eigen jobregistraties onder hardware_tflo_dd6_2026-09-06_v1 en
hardware_compact_tflo_2026-09-07_v1, de chi64-baseline en de
[IBM-uitleg over workload usage](https://quantum.cloud.ibm.com/docs/en/guides/estimate-job-run-time).
