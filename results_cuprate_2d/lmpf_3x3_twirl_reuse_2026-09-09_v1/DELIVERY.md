# Andere 3x3-twirls: hergebruik nog niet onderbouwd

Alle 24 opgeslagen circuits zijn offline gecontroleerd. Voor elk van de zeven
andere twirls en elk van de drie CZ-foldingfactoren (21 vergelijkingen) verschilt
het circuit intern van twirl0. Ook de volledige kanalen van het bevroren
depolariserende ruismodel zijn aantoonbaar verschillend. De eenvoudige route
'dezelfde kern, alleen een ander terminal uitleesmasker' is dus niet van toepassing.

Dit is GEEN nieuw bewijs dat de hardwarewaarden slecht zijn, dat iedere
observable verschilt, of dat een andere analytische transportmethode onmogelijk
is. Wel ontbreekt de onderbouwing om de twirl0-operatoren/gewichten rechtstreeks
op de andere twirls of op een acht-twirlgemiddelde toe te passen.

## Gecontroleerde native circuits

Archiefjob: daem7r642tqs73autong, backend ibm_phoenix, 18 actieve qubits,
3x3 spinvol Hubbard, U=8, T=0.4, twee symmetrische circuitstappen.
Foldingfactoren 1/2/3 behouden respectievelijk 1008/2016/3024 CZ-gates.
De CZ-volgorde per draad is gelijk tussen de twirls; de interne
eenqubit-gates verschillen op alle 18 draden, ook na negeren van de volgorde
van gates op verschillende, onafhankelijke draden.

Onderstaande tabel betreft factor1, zonder metingen. De laatste kolom is
een dimensieloos wiskundig kanaalkenmerk, NIET een foutpercentage.

| Twirl | Native gates | Diepte | X-gates | Delta genormaliseerde logdet versus twirl0 |
|---|---:|---:|---:|---:|
| 0 | 5695 | 629 | 550 | 0 |
| 1 | 5727 | 629 | 575 | +0.003131124 |
| 2 | 5794 | 630 | 566 | -0.005695557 |
| 3 | 5722 | 629 | 588 | -0.008382355 |
| 4 | 5717 | 633 | 555 | -0.000481900 |
| 5 | 5690 | 622 | 568 | -0.001378701 |
| 6 | 5688 | 636 | 546 | +0.008598136 |
| 7 | 5720 | 631 | 557 | +0.002880201 |

De SX- en CZ-bijdragen aan dit kanaalkenmerk zijn hier gelijk tussen twirls;
het verschil komt van de X-gates, gewogen met de foutparameters op hun fysieke
qubits. Meer X-gates betekent daardoor niet automatisch een grotere bijdrage.
Virtuele RZ-gates hebben in dit model nul fout. Factor2/3 geven dezelfde
verschillen ten opzichte van hun eigen twirl0, op afrondingsniveau.

## Wat is wiskundig gecontroleerd?

Voor een k-qubit depolariserende gate met vervalfactor exp(-lambda) geldt:

    L(E) = log(abs(det(E)))/4^n
         = -sum_g (1 - 4^(-k_g))*lambda_g.

De formule volgt uit de lokale Pauli-transfermatrix en de multiplicativiteit
van determinanten; de gates hoeven NIET onderling te commuteren. Ideale
unitaire uitleesmaskers of Pauli-framewijzigingen veranderen deze determinant
niet. De volledige 18-qubit superoperator wordt nergens opgebouwd.

Ongelijke L-waarden sluiten identieke VOLLEDIGE modelkanalen uit. Ze zeggen
niet dat iedere specifieke Heisenberg-operator ongelijk of niet-proportioneel
is. Ook geeft gelijkheid van L geen bewijs van kanaalgelijkheid. Daarom is
dit een negatieve hergebruikdiagnose, geen volledige equivalentietest.

## Verificatie en budget

- 58 tests geslaagd; bestaande L-MPF-tests behouden.
- Onafhankelijke reconstructie van de gatefouten uit het kalibratiearchief.
- 130 verschillende lokale matrices met expliciete Pauli-sporen gecontroleerd.
- Zes volledige driequbit-matrixcontroles, met niet-commuterende gates,
  nulruislimiet, ruisschaling en ideaal uitleesmasker.
- Maximale afwijking in de onafhankelijke archiefberekening: 1.78e-15.
- Maximale afwijking voor de volledige driequbit-matrixcontrole: 2.08e-16.
- Analyse: 12.50 s; onafhankelijke audit: 2.94 s, exclusief interpreter/importstart.
- Geen target-bitstrings opnieuw gelezen of gescoord; geen nieuwe TN-staten.
- Geen nieuwe QPU-run, kosten, gewijzigde hardwarewaarden, publicatie of push.

## Vervolg binnen beperkt budget

[Voorbereide twirl1-controle](NEXT_TWIRL1.md): eerst alleen het centrale Z_up,
met eigen operatorberekeningen bij chi64 en chi128. Twirl1 is gekozen op
volgnummer, niet op gemeten nauwkeurigheid. Geen automatische batch voor zeven
twirls. De eerdere negatieve doublonwaarde en onbesliste betrouwbaarheidsintervallen
blijven ongewijzigd; nog geen groen licht voor 6x6.

De physics-verificatieskill heeft deze kanaalcontrole als voorwaarde voor
hergebruik toegevoegd en houdt modelbewijs gescheiden van hardwarevalidatie.

