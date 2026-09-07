# Bonsai-proef: correct, maar niet shallow

Het volledige6x6-model en de oorspronkelijke eindige-circuit-evolutie zijn behouden. Geen nieuwe hardware-run.

| Representatief volledig circuit met controle-twirl | CZ | CZ-lagen | Totale diepte | Geraamde circuitduur |
|---|---:|---:|---:|---:|
| Bestaand compact | 15400 | 564 | 2030 | 72.252 us |
| Bonsai: minste CZ | 14338 | 5080 | 17705 | 586.812 us |
| Bonsai: kortste duur | 15234 | 5069 | 17290 | 574.660 us |

De laagste CZ-telling is 6.9% lager. De kortste geschatte Bonsai-duur is nog 7.95 keer zo lang.
Alle geteste Bonsai-varianten zijn dieper dan de bestaande compacte route.
Gemiddeld aantal CZ per CZ-laag: bestaand 27.30; snelste Bonsai 3.01. Dit toont het verlies aan parallelisme; het is geen fidelitymaat.

## Wat is gebouwd en gecontroleerd?

- Hardware-afhankelijke ternaire bomen op de oude72-qubitselectie en een compacte72-qubitrechthoek.
- Twee boomlabelingen; de tweede verlaagt de maximale bezettingspariteit van16 naar4 qubits op de rechthoek.
- Annealing van Majoranaparen, zowel op poortkosten als met een extra straf voor de drukst belaste CZ-qubit.
- Native lokale pariteitsnetwerken zonder SWAP-router; tijdelijke Steiner-wires blijven quantumdata en worden volledig hersteld.
- Een X-only Fock-voorbereiding en de bijbehorende GF2-uitlezing voor lading, spin en doublons.
- Zeven basistests plus aanvullende native2x2/2x3-toestandscontroles voor de tweede labeling.
- Alle144 Majoranas zijn op de72-qubitmapping op anticommutatie gecontroleerd; geen volledige72-qubit-statevector gesimuleerd.

De maximale kleine-systeemtoestandsafwijkingen na nativecompilatie liggen onder1e-12. Alle Hamiltontermen, globale fasen, fermiontekens, beginbezettingen en T=0,4 blijven behouden.
De cijfermatige testresultaten staan in de verification.json-bestanden van beide proefmappen.

## Interpretatie en beperkingen

Een boomgebaseerde mapping verkort sommige operatoren, maar het expliciet berekenen en terugherstellen van veel pariteiten laat poorten op gedeelde qubits na elkaar plaatsvinden.
De telling daalt licht; de veel hogere CZ-diepte maakt de huidige implementatie ongeschikt als shallow opvolger.
Dit is geen onmogelijkheidsbewijs voor Bonsai en geen volledige reproductie van de Boston-paper.
Anders dan die paper is hier geen qDRIFT gebruikt en is de tijd of modelinhoud niet verkort.
Dezelfde ideaal-eindige-circuitreferentie blijft dus bruikbaar; de niet-convergente chi64-referentie wordt daarmee niet exact.
Duren komen uit de opgeslagen kalibratie en bevatten voorbereiding/uitlezing, maar geen reset, rep_delay, queue of nieuwe hardwaremeting.
De nieuwe ruwe bits zijn geen directe fermionbezettingen. Masker en GF2-pariteiten zijn opgeslagen; hardware-readoutmitigatie en een nieuwe ZNE-meetbatch zijn nog niet gevalideerd.
Er is geen quantumvoordeel, hardwarefidelitywinst of extra QPU-toestemming geclaimd.

## Bewaren en volgende beslissing

Alle8 controle-twirlkandidaten en hun ongetwirlde circuits blijven bewaard, inclusief minder goede varianten.
De aanvullende labeling/load-proef is toegevoegd nadat de eerste labeling lange bezettingspariteiten liet zien; geen wijziging van de fysica.
De physics-skill stuurde de onafhankelijke operator-, decoder-, toestands- en resourcecontroles.
Geen nieuwe hardware indienen met deze kandidaten. Een andere tijdsevolutiedecompositie is een aparte keuze, met eigen referentie- en foutcontrole.
Bronnen: [Bonsai](https://arxiv.org/abs/2212.09731), [Boston-paper](https://arxiv.org/html/2608.25024).
