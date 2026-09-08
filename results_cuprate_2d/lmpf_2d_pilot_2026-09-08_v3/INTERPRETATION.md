# Interpretatie: interessante kleine pilot, nog geen 6x6-hardwarecorrectie

De L-MPF-overlapmethode is toegevoegd aan het 2D-project en uitgevoerd op een
2x2 Hubbard-systeem met acht qubits. Het ruismodel is afgeleid van opgeslagen
Nighthawk-kalibratie, maar is niet geleerd of gevalideerd op nieuwe hardwaredata.
Er zijn geen nieuwe QPU-seconden gebruikt.

## Wat is positief?

Bij 512 shots per ruisniveau heeft de volledige chi=1 L-MPF-variant een
modelvoorspelde RMSE van 0.0704 voor lading, 0.0758 voor spin en 0.0443 voor
doublons. Dit omvat zowel systematische afwijking als shotvariantie; het is
geen gemeten hardwarefout en geen uitspraak over 6x6.

Tegenover lineaire ZNE is de spinfout ongeveer 2.36 maal kleiner en de
doublonfout 2.12 maal kleiner. De ladingsfout is ongeveer 6% groter. Er is dus
een gericht voordeel in dit model, geen algemene overwinning van L-MPF.

De puur klassieke chi=1-TN geeft voor lading/spin systematische fouten van
0.1264/0.1639. De hybride variant zit daar, zelfs met shotvariantie, onder.
Voor doublons is de puur klassieke fout juist kleiner: 0.0139 tegen 0.0443.
Dit ondersteunt het idee "goedkope TN-informatie kan noisy metingen helpen"
voor sommige observabelen, niet de uitspraak dat de hybride route hier alles
beter berekent. Een exacte klassieke referentie is op acht qubits bovendien
eenvoudig beschikbaar. Quantum advantage is hiermee niet aangetoond.

## Wat werkte niet goed?

- Een chi=2-loopcontractie produceerde NaN; beide bijbehorende fits zijn
  afgewezen. Andere observabelen zijn hierdoor niet van backend verwisseld.
- Exacte contractie van diezelfde chi=2-TN maakt de overlapberekening mogelijk,
  maar ongeregulariseerde coëfficiënten versterken soms de shotruis enorm.
  De totale doublon-RMSE wordt dan 5.2247. Dit negatieve resultaat blijft staan.
- Zelfs L-MPF met de exacte overlap-orakelberekening is zonder regularisatie
  bij 512 shots vaak slechter: zeer kleine systematische fout garandeert geen
  kleine totale fout. De vooraf vastgelegde ridge-variant maakt dit stabieler.
- Chi=1 versus chi=2 is geen convergentiebewijs. Bij chi=1 zijn alle TN-banden
  triviaal; dit valideert niet de bruikbaarheid van loopcorrecties bij grotere
  bond dimension of op een groot tweedimensionaal rooster.

## Wat is nodig voor de bestaande 6x6-resultaten?

De echte readout-plus-CZ-folding-archieven van 3x3 en 6x6 zijn ingelezen en
klaargezet met shotcovariantie en gedeelde readout-kalibratieonzekerheid.
De volgende stap is een gevalideerde, voldoende zuinige overlapberekening
voor die eigen circuits, met een geleerd of onafhankelijk getoetst ruismodel.
CZ-folding schaalt niet alle ruis zoals in deze pilot. Coëfficiënten van acht
qubits mogen niet worden hergebruikt voor 72 qubits.

De volledige pilot kostte 841.059 seconden inclusief exacte validatie,
meerdere TN-methoden en diagnostiek. Dat is geen productietiming en niet
vergelijkbaar met de historische 150-seconden/7-seconden-claim voor 6x6.

[Alle tabellen en verificatie](DELIVERY.md). De 23 tests en de onafhankelijke
herberekening uit de opgeslagen data slagen; alle eerdere mislukkingen,
bitstrings, coëfficiënten, broncode-snapshots en hashes zijn bewaard.
