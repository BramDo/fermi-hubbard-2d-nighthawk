# Compacte quantumcircuitfamilie: circa33% korter, TFLO-structuur behouden

Een nieuwe PARAMETERIZED 6x6-circuitfamilie is gebouwd en onafhankelijk
gecontroleerd. Bij dezelfde opgeslagen Nighthawk-kalibratie daalt de geraamde
duur van120-121us naar80.3-80.5us. De vier twirls bevatten circa65% minder
fysieke een-qubitpulsen. Alle36 U/tijd-bindingen houden dezelfde poortstructuur.
Dit is een concrete verbetering van de circuitkandidaat, nog geen gemeten
verbetering van quantumobservabelen. Er is geen hardwarejob ingediend.

## Vergelijking binnen dezelfde TFLO-familie

| Twirl | Oude duur, us | Compact, us | X+SX oud | X+SX compact | Diepte oud | Diepte compact |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 120.212 | 80.252 | 104847 | 36527 | 4360 | 2915 |
| 1 | 121.012 | 80.412 | 105496 | 36337 | 4376 | 2914 |
| 2 | 120.372 | 80.452 | 105448 | 36473 | 4385 | 2916 |
| 3 | 120.612 | 80.292 | 104786 | 36441 | 4350 | 2926 |

Duurreductie33.16-33.55%; fysieke1q-pulsreductie65.16-65.56%.
In alle gevallen blijven20,736CZ en584CZ-lagen over. De twee-qubitbelasting
is dus NIET verminderd. Ook een compacter circuit kan nog te veel ruis geven.
Korter betekent niet automatisch een evenredig kleinere observabelfout.

Dit is niet de oude15,400CZ-familie met een bound72-us-kandidaat. Die oudere
variant was voor een vaste U/tijd geoptimaliseerd. Hier is de complete
parametrische familie van de daadwerkelijk uitgevoerde TFLO/DD-pilot behouden,
inclusief de symbolische U=0-trainingsmogelijkheid en exact dezelfde layout.

## Wat is veranderd, wat niet?

- Alleen constante native1q-segmenten zijn samengevoegd en opnieuw exact
  gesynthetiseerd tot RZ/SX/X, voor het invullen van U en T.
- CZ en symbolische RZ-ankers blijven in dezelfde volgorde per qubit.
- De conservatieve CZ-canceltest vond geen verwijderbare paren; er zijn geen
  CZ-gates of fysische interacties weggehaald.
- Zelfde36sites/72modi,32deeltjes,U=8,t=1,t'=-0.25,T=0.4,twee stappen.
- Alle fermiontekens, beginconfiguratie, globale fase en uitleesmapping zijn
  behouden, binnen de gecontroleerde numerieke synthesetoleranties.
- Dezelfde vier twirlseeds; alle uitleesmaskers zijn ook gelijk gebleven.
- DD wordt in deze kandidaat niet toegevoegd. De eerdere DD-test liet geen
  aantoonbare winst zien. Een eventuele nieuwe DD-arm moet apart worden getest.

De positieve verwachting is minder ruis door kortere blootstelling en minder
fysieke1q-pulsen. Het effect op echte data moet nog worden gemeten; met20,736CZ
kan de dominante foutbron nog steeds overblijven.

## Waarom dit bruikbaar is voor TFLO

Het circuit wordt opgeschoond terwijl T en U nog symbolisch zijn. Daarna
veranderen alleen parameterwaarden, niet de poorten of hun posities.
Zes U=0-trainingstijden, twee U=0-holdouts en het U=8-doel zijn voor elk van
de vier twirls gebonden en gecontroleerd:36/36 dezelfde skeleton en aantallen.
De productiecircuits mogen later niet na het binden opnieuw worden geoptimaliseerd.

Dit verzekert een gematchte circuitfamilie, NIET dat de affine TFLO-fit goed
zal werken. Nieuwe holdouts moeten slagen. Training op MPS/U=8-antwoorden,
clipping van negatieve kansen of selectie op een mooi N zijn geen vervanging.

## Onafhankelijke controles

- Zes tests geslaagd, waaronder een volledige2x2-netwerkunitariteit en
  willekeurige toestanden bij verschillende U/T, plus geldige/ongeldige CZ-
  cancelgevallen, symbolische ankers, twirls en uitleesmapping.
- Volledige72-mode-opschoning:43,736 lokale2x2-segmenten, inclusief symbolische
  ankers en globale fase, in de eerste native ronde gecontroleerd.
- Rechtstreeks vergeleken met vijf DAADWERKELIJKE oude providerinvoercircuits:
  alle vier U=8-doeltwirls en een U=0-holdout. Alleen delays/barriers zijn
  voor deze ideale vergelijking verwijderd, geen dynamica of DD-pulsen.
- Maximaal lokaal segmentverschil9.16e-16; globale faseafwijking1.58e-11.
- Vier onafhankelijke Qiskit-SDK-duurschattingen bevestigen de eigen integer-
  dt-klok. Beide gebruiken dezelfde opgeslagen target, geen verse kalibratie.
- Vijf parametrische QPY-bestanden byte-exact heen/terug getest en voorzien
  van verliesloze gzip-kopieen. Originelen blijven op schijf.

De worker kostte134.77s lokaal, de extra providerinput/SDK-controle44.97s.
Geen72-qubit-statevector, geen klassiek chi128-werk, geen langere-tijdscan,
geen providerverbinding en0 nieuwe QPU-seconden. De bestaande resultaten en
frozen-source-archieven zijn niet gewijzigd.

## Volgende quantumstap

Een gerichte nieuwe hardwarepilot kan origineel en compact binnen dezelfde
job vergelijken, met readout, twirling en dezelfde vaste TFLO-procedure.
Meet eerst de fout op exact berekenbare U=0-holdouts en vergelijk pas daarna
het U=8-resultaat. Zo toetsen we daadwerkelijke quantumkwaliteitswinst.

Het bijgevoegde PILOT_VOORSTEL.md beschrijft de vergelijking. Dat is nog geen
toestemming of submission-ready job: verse ISA/kalibratie/budgetcontrole en
nieuwe expliciete toestemming zijn vereist. Eerdere15s-toestemming is verbruikt.

De physics-skill bepaalde de parametrische gelijkwaardigheid, onafhankelijke
controles, complete bewaring en het uitstellen van fout-/advantageclaims.
Synthese: [IBM OneQubitEulerDecomposer](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.synthesis.OneQubitEulerDecomposer).
