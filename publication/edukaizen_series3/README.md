# Edukaizen serie 3 — conceptpakket

Negen Nederlandstalige artikelen plus een seriepagina over 2D Hubbard op
Nighthawk. De rode draad is ons beperkte lokale doel: circa20x minder
geregistreerde QPU-tijd dan de rekenkerntijd van de huidige chi64-baseline.
Geen claim van gelijke nauwkeurigheid of end-to-end quantum advantage.

Begin bij [de seriepagina](nl/00_series.md). `nl/` bevat de bewerkbare
Markdown-bronnen; `wordpress/nl/` het HTML-conceptpakket; `preview/00.html`
een lokale leesweergave. Maak deze uitvoer met `python scripts/build_series3.py`.
De renderer is hergebruikt uit de bestaande Edukaizen-serie2-workflow.

Alle tien manifestitems hebben status draft en post_id=null. De voorgestelde
slugs zijn geen bewijs dat de pagina's al bestaan. Er zijn geen WordPress-
mutaties, menuwijzigingen, uploads of publicaties uitgevoerd. De bestaande
1D- en 2D-series blijven onveranderd.

Formules blijven als `[latex syntax="display"]...[/latex]` in het WordPress-
pakket; de offline preview toont hun broncode. Live MathJax-rendering moet bij
de latere publicatiestap worden gecontroleerd. Engelstalige vertaling is nog
niet gemaakt. De nieuwe repository is voorlopig privé; de artikelen vermelden
dat de repositorylink toegangsrechten vereist.

## Redactionele controles

- Alle getallen zijn gekoppeld aan theory/RESULTS_AND_CLAIMS.md of de
  bewaarde Google-conversie, niet aan afgeronde herinneringen.
- De 7s- en8s-resultaten zijn verschillende jobs. De laatste omvat beide armen.
- Ruwe en gemitigeerde waarden worden niet door elkaar gebruikt.
- N32 is een modelconstraint; gemeten N wordt niet vervangen.
- Chi64 is niet geconvergeerd; mislukte TFLO-holdouts blijven genoemd.
- Boston/Heron wordt niet als Nighthawk aangeduid.
- Papierclaims, onze reproductie en toekomstvoorstellen blijven gescheiden.

Voor publicatie: controleer actuele hub/slug/parent-IDs, behoud MathJax,
maak een serverbackup, publiceer idempotent na expliciete toestemming en
verifieer iedere URL en eventuele navigatie live. Zet niet automatisch deze
concepten in een bestaande serie2-pagina.
