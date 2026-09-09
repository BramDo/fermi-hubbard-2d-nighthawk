# Exacte ideale norm: centrale overlapcontrole slaagt, gewichten onveranderd

9 september 2026. De aanvullende offline normcontrole is uitgevoerd op drie
centrale 3x3-operatoren, steeds twirl 0 van het opgeslagen job
`daem7r642tqs73autong` op `ibm_phoenix`. De bestaande Z_up/Z_down-data op
chi64/128 en ZZ-data op chi128/256 zijn hergebruikt. Geen nieuwe
tensorpropagatie, QPU-job, hardwarewaarden of 6x6-run.

## Wat nu slaagt

| Operator | Verfijning | Oude Gram-verandering | Gram met exacte norm | G-verandering | b-verandering | Coefficient-L1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Z_up | chi64->128 | 0.3639% | 0.0857% | 0.0388% | 0.1558% | 0.012577 |
| Z_down | chi64->128 | 0.2962% | 0.0791% | 0.0239% | 0.1206% | 0.013187 |
| ZZ | chi128->256 | 1.3098% | 0.1803% | 0.1311% | 0.4988% | 0.032187 |

De aanvullende lokale controle vereist <=1% voor de normgecorrigeerde volledige
Gram, afzonderlijk <=1% voor G en b, en <=0.05 voor de coefficient-L1-verandering.
Alle drie operatoren voldoen hieraan. De aparte G/b-controles voorkomen dat een
grote bekende constante veranderingen in kleine ruisblokken verbergt.

Dit protocol is opgesteld na de vorige componentdiagnose, op reeds bekende
data. Het is geen geblindeerde preregistratie, onafhankelijke dataset of
rigoureuze truncatiefoutgrens. De oude raw-Gram-beoordeling is behouden:
Z_up/Z_down slagen daarin, ZZ blijft daarin mislukt. De eerdere uitkomst is
niet overschreven of met terugwerkende kracht als geslaagd gepresenteerd.

## Waarom de norm exact bekend is

In de gebruikte genormaliseerde Hilbert-Schmidtconventie geldt, voor d=2^18,
een Pauli-product O en de ideale unitaire circuitoperatie U:

```text
A = U_dagger O U
O_dagger O = I,  U_dagger U = U U_dagger = I
A_dagger A = U_dagger O_dagger U U_dagger O U = I
F00 = Tr(A_dagger A) / d = 1.
```

Dit geldt voor Z8, Z9 en Z8 Z9; een readout-maskerteken +/-1 verandert hun norm
niet. Het argument betreft de ideale circuitarm, niet de fysieke ruiskanalen.
De fysieke voorbereidingspoorten blijven deel van U. De referentie is het
eindige circuit; deze identiteit bewijst geen productformulefoutgrens voor
Hamiltoniaandynamica.

De daadwerkelijke native circuitbestanden zijn gecontroleerd: 20,109 poorten,
57 verschillende kleine poortmatrices, maximale unitariteitsafwijking
2.22045e-16. Met SymPy is daarnaast een niet-triviaal complex unitair
vierdimensionaal voorbeeld exact gecontroleerd: genormaliseerde trace = 1.
Dat is een algebraische/numerieke verificatie, geen nieuwe Lean-certificering.

## Geen verandering van gewichten of hardwareverwachtingen

Alleen F00 is in een afzonderlijke kopie van de Gram vervangen door 1.
G=F[1:,1:] en b=F[1:,0] blijven bit-identiek. Er is geen operatornetwerk
herschaald, geen ruisnorm vervangen en geen bekende deeltjeslading als meting
ingevuld. De oorspronkelijke bronbestanden blijven intact.

Voor de vaste ridge alpha=1/56 minimaliseren we:

```text
F00 - 2 b^T c + c^T G c + alpha ||c||^2,  met sum(c)=1.
```

F00 is een constante in c en komt niet voor in het KKT-stelsel voor de optimale
gewichten. Daarom blijven de gewichten gelijk. Dit is voor zowel ridge als
onregulariseerde fits, op beide chi-niveaus en voor alle drie operatoren
gecontroleerd: maximale verandering is exact 0 in de berekende getallen.
Een onafhankelijke directe KKT-oplossing komt binnen 8.60e-13 overeen met de
oorspronkelijke null-space-oplossing.

Met dezelfde gewichten blijven ook c^T m en c^T Sigma c onveranderd voor elke
vaste vector metingen m en covariantiematrix Sigma. Dat is tevens getest met
synthetische fixtures; er zijn hier geen hardwaregemiddelden opnieuw geanalyseerd.
Deze stap verbetert dus de diagnose van de klassieke overlapberekening, niet
op zichzelf een quantummeetwaarde of de bijbehorende vaste-gewicht-shotfout.

De projectieresiduen veranderen wel: ze stijgen precies met 1-F00. Dat herstelt
een onderschatte ideale normterm en is geen grotere gemeten hardwarefout.

| Laatste niveau | Oorspronkelijk ridge-residu | Met exacte norm |
| --- | ---: | ---: |
| Z_up, chi128 | 0.139589662 | 0.139951689 |
| Z_down, chi128 | 0.105020338 | 0.105385979 |
| ZZ, chi256 | 0.236934957 | 0.243048689 |

Ook de eerder geconstateerde niet-monotone ideale ZZ-verwachting verandert niet:
de absolute afwijking was 0.006369659 bij chi128 en is 0.008275785 bij chi256.
Die ongunstige controle blijft zichtbaar en wordt niet door een normcorrectie
weggenomen. De residuen zijn voor benaderde G/b en een onbewezen ruissurrogaat,
niet voor de exact bekende fysieke device-Lindbladdynamica.

## Verificatie, tijd en bewijsbestanden

- Alle 40 tests zijn geslaagd: de eerdere 36 en vier nieuwe tests voor de exacte
  normidentiteit, onveranderde gewichten/fixtures, afwijzing van ongeldige
  oorspronkelijke Grams en gevoeligheid van de afzonderlijke blokcontroles.
- Een niet-PSD originele Gram wordt afgewezen voordat F00 wordt vervangen.
  De correctie mag dus geen ongeldige oorspronkelijke berekening verhullen.
- De onafhankelijke auditor controleert 12 fits, alle bron-/inputhashes in het
  nieuwe manifest, de onveranderde G/b-blokken, residuverschuivingen en beide
  classificaties. Maximale residuverschuivingsfout: 0; gewichtsverandering: 0.
- De runfunctie duurde 4.677 s, inclusief tests en native-poortcontrole;
  de onafhankelijke auditfunctie 0.504 s. Imports, launcher, documentatie en Git
  vallen buiten die timers. De eerdere chi128/256-berekeningen blijven onderdeel
  van de totale klassieke voorbereiding; dit is geen nieuwe snelheidswinstclaim.
- Alle nieuwe input-JSONs, geselecteerde numerieke broncode, tests, Grams, fits en
  beide beoordelingen zijn bewaard. Grote tensorbestanden zijn niet opnieuw
  gekopieerd. Geen installatie, GitHub-push of publicatie.

De physics-verificatieskill houdt deze aanvullende, retrospectieve lokale
stabiliteitscontrole apart van een onafhankelijke fysische validatie. Nog open:
alle 27 observabelen, acht twirls en hun kruistermen, device-noise-validatie,
projectiebias en shot-/kalibratieonzekerheid. De oorspronkelijke volledige
3x3-hardware-no-go voor lading/doublons is hiermee niet opgeheven. Geen 6x6.

## Volgende gerichte stap

Een beperkte, exploratieve vergelijking van deze drie vaste gewichten met de
bijpassende opgeslagen twirl 0-hardwaremetingen, inclusief readout- en
shotonzekerheid, is nu zinvoller dan alleen vanwege F00 automatisch chi verhogen.
Gebruik nooit een enkele-twirlcoefficient op het acht-twirlhardwaregemiddelde.
Pas na een passende kwaliteitscontrole kan verdere opschaling worden overwogen.

## Reproduceren

In de bestaande WSL-Qiskitomgeving, vanuit de repository, met een nieuwe map:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B lmpf_2d/norm_control.py --output NEW_DIRECTORY
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B lmpf_2d/verify_norm_control.py NEW_DIRECTORY
```

- [Vervolgprotocol en bronhashes](plan.json).
- [Volledige resultaten en fits](results.json), [hashmanifest](sha256.json).
- [Onafhankelijke audit](verification/verification.json), [verificatienotitie](VERIFICATION.md).
- [Voorgaande ZZ-diagnose](../lmpf_3x3_zz_chi256_2026-09-09_v1/DELIVERY.md).
