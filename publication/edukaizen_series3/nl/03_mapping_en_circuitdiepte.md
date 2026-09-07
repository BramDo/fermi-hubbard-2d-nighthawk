---
part: 3
title: "Van 2D-rooster naar hardware: mapping en circuitdiepte"
slug: "hubbard-nighthawk-serie-3-03-mapping"
status: draft
language: nl
---
# Van 2D-rooster naar hardware: mapping en circuitdiepte

De belangrijkste optimalisatievraag was niet hoeveel qubits we konden
reserveren, maar hoeveel foutgevoelige bewerkingen nodig waren om onze
opgave op verbonden hardware uit te voeren. Een 72-qubit circuit kan
bruikbaar of onbruikbaar zijn, afhankelijk van routing en diepte.

## Drie maten die gemakkelijk door elkaar lopen

Poortaantal telt alle bewerkingen. Diepte telt opeenvolgende lagen; poorten
op verschillende qubits kunnen soms tegelijk plaatsvinden. Fysieke duur
houdt bovendien rekening met werkelijke poorttijden en wachttijden.

Daarom kan een optimalisatie minder éénqubitpulsen en een kortere duur
opleveren zonder het aantal tweequbitpoorten te veranderen. Het omgekeerde
kan ook: een kortere logische expressie kan na hardware-routing toch duurder
worden. We bewaren deze drie maten afzonderlijk.

## Fermionic SWAP-netwerken

Een fSWAP brengt fermionmodi langs elkaar terwijl het vereiste minteken
voor dubbele bezetting behouden blijft. Door een netwerk van zulke
verwisselingen kunnen de juiste interacties op geschikte hardwareparen
plaatsvinden. De boekhouding van de uiteindelijke modenvolgorde is net zo
belangrijk als de poorten zelf: anders lezen we de juiste bit op de
verkeerde fysische site uit.

In eerdere compilatiestappen verlaagde de gekozen netwerkroute het aantal
CZ-poorten sterk. Die historische circuitfamilie is niet identiek aan iedere
latere trainings- of twirlingfamilie. Een oud getal van 15.400 CZ mag dus
niet worden gecombineerd met de uitkomst van een anders samengestelde run.

## Origineel tegenover compact

De laatste gepaarde 6x6-test gebruikte twee versies van dezelfde
geparametriseerde circuitfamilie. De compacte versie vereenvoudigde de
éénqubitstructuur vóór het invullen van parameters. Beide armen behielden
20.736 CZ-poorten en 584 CZ-lagen.

De gewone poortdiepte ging grofweg van 4.350–4.385 naar 2.914–2.926.
De geschatte ingeplande duur daalde van ongeveer 123–124 naar 81
microseconden. Dat is een serieuze compilerverbetering. Toch waren de
gemeten, gemitigeerde observabelen in deze ene proef niet beter voor compact.

Een korter circuit is dus een middel, geen eindbewijs. De meting moet laten
zien of de relevante informatie daadwerkelijk beter behouden blijft.

## Ancilla's, Bonsai en qDRIFT

Extra qubits kunnen bepaalde pariteitsbewerkingen vereenvoudigen, maar
voorbereiding, stabilisatoren en routing kunnen de winst weer opeten.
Onze ancilla- en Bonsai-proeven zijn daarom met volledige resourcekosten
bewaard, ook wanneer ze geen verbetering gaven.

Bonsai bouwt een hardware-afhankelijke boomencoding. Dat is interessant op
heavy-hex hardware, maar een goede Boston-mapping is niet automatisch een
goede Nighthawk-mapping. qDRIFT is weer iets anders: het verandert de
tijdsbenadering door Hamiltoniaantermen te bemonsteren. Daarbij hoort een
eigen benaderingsfout, niet alleen een nieuw poortaantal.

Bronnen: scheduling_validation.json van de gepaarde 6x6-run,
BONSAI_AUGUST_2026_REVIEW.md, PA_ANCILLA_PROTOCOL.md en
[de oorspronkelijke Bonsai-publicatie](https://arxiv.org/abs/2212.09731).
