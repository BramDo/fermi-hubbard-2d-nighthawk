# PA: correct prototype, nog geen shallow Nighthawk-circuit

PA is geimplementeerd met 72 datamodi en 36 ancillas. De uitgevoerde offline resourceproef levert geen betere hardwarekandidaat.

| Volledig circuit met controle-twirl | Vorige compacte variant | Beste geteste PA |
|---|---:|---:|
| Qubits in encoding | 72 | 108 |
| CZ-poorten | 15400 | 21337 |
| CZ-lagen | 564 | 3404 |
| Totale diepte | 2030 | 10772 |
| Geraamde circuitduur | 72.252 us | 397.968 us |

De tabel telt voorbereiding en data-uitlezing mee. De nieuwe kandidaten gebruiken een controle-twirl, geen volledige ZNE-batch.
Dit zijn circuitresources uit opgeslagen kalibratie, geen nieuwe hardwaremetingen, foutmarges of advantage-resultaten.
De beste PA gebruikt een andere symmetrische Trottervolgorde. Dit is dus geen matched-accuracy speed comparison.

## Wat is wel gevalideerd?

11 verschillende tests slagen. PA-edgealgebra is op 2x2, 2x3 en 6x6 gecontroleerd.
Op 2x2 komen alle Hubbard-hoppingtermen en onsite-interacties in beide pariteitssectoren overeen met een onafhankelijke occupation-basisreferentie.
De volledige kleine-systeemdynamica klopt met de eigen JW-referentie. Tests omvatten chemische potentiaal, willekeurige toestanden en globale fase.
De 6x6-voorbereiding is met een Clifford-tableau op alle 25 loopstabilisatoren en 72 beginbezettingen gecontroleerd.
De 11 extra rand-/gauge-vrijheidsgraden zijn deterministisch aangevuld door de stabilizer-synthese; dit zijn geen extra fermionmodi.
Geen volledige 108-qubit-statevector is gesimuleerd.

## Waar verdwijnt de winst?

Gedeelde pariteitssynthese vermindert in de oorspronkelijke eventvolgorde de ongerouteerde evolutie van 11.411 naar 6.194 CZ-poorten.
De laaggegroepeerde ongerouteerde evolutie heeft 5.996 CZ-poorten, 454 CZ-lagen en totale diepte 1.112, maar sluit voorbereiding en chip-routing uit.
Na voorbereiding en routing worden deze cijfers veel slechter. De afzonderlijk gecompileerde voorbereiding alleen heeft al 852 CZ-poorten en 375 CZ-lagen.
De gerichte row-fold-layout eindigt met 25.786 CZ-poorten, 4.613 CZ-lagen en totale twirl-diepte 14.404; ook die is afgewezen.
Ancillas geven dus geen automatische dieptewinst. Dit beperkt de huidige synthese/layout, niet PA als methode.

## Wat ontbreekt?

De paper-specifieke XYZ-bloksynthese, een passende volledige PA-layout en een ondiepe gezamenlijke ancilla-voorbereiding zijn nog niet gerealiseerd.
De paperdiepte van 35 fSIM-lagen per Trotterstap is niet gereproduceerd en mag niet als Nighthawk-CZ-diepte worden gebruikt.
Voor de gewijzigde layered-volgorde blijven een nieuwe klassieke referentie en Trotterconvergentie noodzakelijk.
Alle t, t-prime, U en fermiontekens zijn behouden. Geen nieuwe hardware of chi=128 gestart.

## Bewaren en afwijkingen

v1 en v2 bevatten behouden softwarefouten in de rapportage/testinterface, beschreven in FAILED.md. De fysische modeltests faalden niet.
v3 en de gevouwen-layoutproef zijn volledig afgerond en hebben hashmanifests.
De physics-skill stuurde de code-subruimte-, teken-, voorbereidings- en onafhankelijkheidscontroles.
Bron: [Algaba et al., Quantum 8,1327](https://arxiv.org/html/2302.01862v3).
