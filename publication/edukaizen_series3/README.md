# Edukaizen serie 3 — 2D Local Quantum Advantage

Gepubliceerd op 7 september 2026:
[2D Local Quantum Advantage](https://edukaizen.nl/2d-local-quantum-advantage/).
De hoofdpagina (ID 1089) bevat negen Nederlandstalige artikelen (IDs 1090–1098).
Een eigen menutak en vorige/volgende-links verbinden de serie.
Zie [publicatieregistratie](releases/2026-09-07_v1/DELIVERY.md) voor alle IDs,
verificatie en de afbakening van de visuele controle.

Negen Nederlandstalige artikelen plus een seriepagina over 2D Hubbard op
Nighthawk. De rode draad is ons beperkte lokale doel: circa 20x minder
geregistreerde QPU-tijd dan de rekenkerntijd van de huidige chi64-baseline.
Geen claim van gelijke nauwkeurigheid of end-to-end quantum advantage.

Begin bij [de seriepagina](nl/00_series.md). `nl/` bevat de bewerkbare
Markdown-bronnen; `wordpress/nl/` het HTML-conceptpakket; `preview/00.html`
een lokale leesweergave. Maak deze uitvoer met `python scripts/build_series3.py`.
De renderer is hergebruikt uit de bestaande Edukaizen-serie2-workflow.

Het oorspronkelijke `manifest.json` bewaart het conceptstadium: alle tien
items staan daarin nog op draft en post_id=null. Dit is historische invoer,
niet de huidige publicatiestatus. De definitieve HTML, slugs, IDs en checksums
staan in `releases/2026-09-07_v1/`. De bestaande 1D- en 2D-series zijn behouden.

Formules blijven als `[latex syntax="display"]...[/latex]` in het WordPress-
pakket; de offline preview toont hun broncode. Live HTML bevat MathJax-markeringen
en geen onverwerkte shortcodes. Visuele browsercontrole kon niet worden afgerond
door een onbeschikbare Chrome-verbinding. Engelstalige vertaling is nog
niet gemaakt. De nieuwe repository blijft privé; de artikelen vermelden
dat de repositorylink toegangsrechten vereist.

## Redactionele controles

- Alle getallen zijn gekoppeld aan theory/RESULTS_AND_CLAIMS.md of de
  bewaarde Google-conversie, niet aan afgeronde herinneringen.
- De 7s- en 8s-resultaten zijn verschillende jobs. De laatste omvat beide armen.
- Ruwe en gemitigeerde waarden worden niet door elkaar gebruikt.
- N32 is een modelconstraint; gemeten N wordt niet vervangen.
- Chi64 is niet geconvergeerd; mislukte TFLO-holdouts blijven genoemd.
- Boston/Heron wordt niet als Nighthawk aangeduid.
- Papierclaims, onze reproductie en toekomstvoorstellen blijven gescheiden.

Voor een volgende publicatie: controleer actuele hub/slug/parent-IDs, behoud MathJax,
maak een serverbackup, publiceer idempotent na expliciete toestemming en
verifieer iedere URL en eventuele navigatie live. Zet niet automatisch deze
concepten in een bestaande serie2-pagina. Herhaal de release niet blind:
`transport.json` en `partial_receipt.json` documenteren de eerste poging;
`publish_receipt.json` en `public_verification.json` bevestigen de afronding.
