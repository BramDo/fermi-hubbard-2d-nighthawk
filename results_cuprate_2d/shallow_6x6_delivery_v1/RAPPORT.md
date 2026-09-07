# Quantumcontrole 6×6: compacter, maar CZ-belasting blijft hoog

Geen nieuwe QPU-run; geen wijziging van bestaande hardwaredata of van de klassieke χ=64-resultaten.

## Wat is aangepast?

Alleen opeenvolgende één-qubitbewerkingen rond de bestaande CZ-poorten zijn samengevoegd.
De volledige Hamiltoniaan met t, t-prime, U en fermiontekens, T=0,4 en twee Trotterstappen blijven behouden.
Alle CZ-poorten, hun volgorde per qubit en de uitleesmapping zijn behouden.
Dit is een gelijkwaardige ideale berekening, geen verkorting van de fysieke evolutie.

| Eigenschap, representatieve twirl | Uitgevoerd | Compacter |
|---|---:|---:|
| CZ-poorten | 15400 | 15400 |
| X/SX-pulsen | 50490 | 26224 |
| Totale diepte | 3241 | 2030 |
| CZ-diepte | 564 | 564 |
| Geraamde circuitduur | 99.732 µs | 72.252 µs |

Dat is 37.4% minder totale diepte, 48.1% minder fysieke één-qubitpulsen en 27.6% kortere geraamde circuitduur.
Alle acht oorspronkelijke twirls zijn opgebouwd en gecontroleerd. Hun nieuwe dieptes liggen tussen 2020 en 2044.
De circuitduur gebruikt de opgeslagen backendkalibratie en is geen nieuwe hardwaremeting of QPU-factuurvoorspelling.

## Waarom is 1D gunstiger?

Een werkelijk 1D-model koppelt vooral naaste buren. De 6×6-2D-lattice heeft daarnaast verticale en diagonale koppelingen.
Onze 6×6 blijft een 2D-fysisch model, ook wanneer de fermionmodi in een 1D-keten worden gerouteerd.
Die ketenmapping gebruikt 71 verbindingen, terwijl binnen de geselecteerde fysieke qubits 108 CZ-verbindingen beschikbaar zijn.
De 37 overige verbindingen zijn niet automatisch gratis bruikbaar: ook bij een andere mapping moeten de fermionpariteiten behouden blijven.

Vóór compilatie bevat het oorspronkelijke netwerk 10.224 fSWAP-blokken, waarvan 9.200 zonder fysische interactie.
Dat betekent niet dat 90% van de uiteindelijke CZ-poorten zomaar kan worden geschrapt. Routing kan nodig zijn om koppelingen lokaal te maken; de compiler verwijdert al een deel van de overhead.

## Andere routes zijn getest, niet blind overgenomen

Drie gerichte swaproutes en drie planners die alleen disjuncte even-fermioninteracties herschikken zijn gecontroleerd.
De gatevolgorde op iedere fermionmodus bleef behouden. Alle alternatieven waren langzamer dan de één-qubit-opschoning.
Bijvoorbeeld: de look12-route verlaagt CZ van 15.400 naar 14.168, maar verhoogt de totale diepte naar 7.722 en de geraamde duur naar 274,52 µs. Dat is geen shallow verbetering.

## Grenzen en volgende beslissing

De beste gevonden variant heeft nog steeds 15.400 CZ-poorten en 564 CZ-lagen. Het belangrijke twee-qubitprobleem is dus niet opgelost.
Opgeslagen T2-waarden van de geselecteerde qubits: minimum 7,49 µs, mediaan 136,05 µs. Dit onderstreept dat circuitduur relevant is, maar is geen berekening van de circuitfideliteit.
De waargenomen hardwarefout kan hiermee niet uitsluitend aan één oorzaak worden toegeschreven.
Voor verdere reductie is een andere 2D-gerichte decompositie/routing een logische kandidaat. Als daarbij niet-commuterende Trottertermen anders worden geordend, verandert het ideale eindige-stappencircuit en moet ook de klassieke referentie opnieuw worden gemaakt.
Nieuwe hardware vereist een apart compleet meetprotocol, verse backend-/budgetcontrole en nieuwe expliciete toestemming. De oude autorisatie wordt niet hergebruikt.

## Verificatie en archief

14 tests zijn geslaagd: volledige kleine-systeemunitariteiten, een willekeurige 2×3-toestand, fermionpermutaties, uitleesmapping en de commutatie van disjuncte even-fermioninteracties.
Op de volledige 72-modecircuits zijn de één-qubitsegmenten afzonderlijk als 2×2-matrices gecontroleerd, inclusief globale fase en onveranderde CZ-volgorde.
Er is geen volledige 72-qubit-statevector gesimuleerd. Geen hardwarefoutverbetering of quantumvoordeel geclaimd.
De physics-skill heeft de gelijkwaardigheidscontroles en het gescheiden bewaren van minder goede kandidaten gestuurd.
Methode: [Qiskit Optimize1qGatesDecomposition](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.transpiler.passes.Optimize1qGatesDecomposition).
De twee volledige proefrondes staan in shallow_full6x6_T04_v1 en shallow_full6x6_frontier_v1; de oorspronkelijke resultaten blijven onaangeroerd.
