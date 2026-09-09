# Centrale hardwaretoets: geen betrouwbare verbetering door deze L-MPF-toepassing

9 september 2026. De drie stabiele centrale coefficientensets zijn toegepast
op de bijpassende opgeslagen twirl-0-metingen van het 3x3-job
`daem7r642tqs73autong`, `ibm_phoenix`. **Deze pilot slaagt niet als
hardwarekwaliteitscontrole.** Er is geen nieuwe QPU-job gestart.

De voorafgaande exacte-normcontrole was geslaagd, maar veranderde de gewichten
niet. Deze hardwaretoets laat zien waarom numeriek stabiele overlapgewichten
niet hetzelfde zijn als nauwkeurige hardwaremitigatie.

## Primaire vergelijking bij gelijk shotbudget

Het gaat om de centrale lattice-site (modi8 en 9), niet om de totale lading N
of om een volledig 3x3-profiel. Spin=n_up-n_down, doublon=n_up*n_down.
De referentie is exact voor het eindige ideale circuit, niet voor foutvrije
Hamiltoniaandynamica zonder productformulefout.

| Methode | Centrale lading | Centrale spin | Centrale doublon |
| --- | ---: | ---: | ---: |
| Exact eindig circuit | 0.404671 | -0.362021 | 0.009685 |
| Readout-only, 64 targetshots | 0.571533 | -0.079346 | 0.043825 |
| Readout + lineaire ZNE, 43/7/14 | 0.271179 | -0.460012 | -0.183805 |
| Readout + vaste L-MPF, 43/7/14 | -0.029469 | -0.712862 | -0.309473 |

Elke primaire methode gebruikt 64 targetshots en dezelfde128 kalibratieshots:
192 toegewezen shots uit het archief per estimator. De gevouwen armen hebben
slechts 7 en 14 shots. Voor de factor1-arm is eenmaal een vaste, vooraf gekozen
seed-permutatie gebruikt om43 gedeelde shots te kiezen; de overige21 worden
alleen door de 64-shotbaseline gebruikt. Geen seed- of subsetselectie op nauwkeurigheid.

De puntschattingen van L-MPF zijn bij dit gelijke budget voor alle drie
grootheden minder nauwkeurig dan zowel readout-only als lineaire ZNE.
Dat is een beschrijving van deze gerealiseerde schattingen, geen statistisch
bewezen algemene inferioriteit van de methode.

| Absolute afwijking tegenover exact | Lading | Spin | Doublon |
| --- | ---: | ---: | ---: |
| Readout-only | 0.166863 | 0.282675 | 0.034140 |
| Lineaire ZNE | 0.133491 | 0.097991 | 0.193490 |
| L-MPF, matched | 0.434140 | 0.350841 | 0.319159 |

## Onzekerheid en fysieke consistentie

10,000 gepaarde bootstrapreplicaties bewaren de gedeelde targetshots en de
correlaties tussen Z_up, Z_down en ZZ. Iedere replicatie gebruikt dezelfde
Jeffreys-readoutkalibratietrekking voor alle armen en methoden.

| Bootstrap-SD inclusief kalibratie | Lading | Spin | Doublon |
| --- | ---: | ---: | ---: |
| Readout-only | 0.075123 | 0.085335 | 0.027286 |
| Lineaire ZNE | 0.189086 | 0.214100 | 0.098307 |
| L-MPF, matched | 0.278384 | 0.283376 | 0.174504 |

De intervallen voor verbetering gebruiken
absolute fout(baseline) - absolute fout(L-MPF): positief is beter voor L-MPF.

| Gepaard 95%-percentielinterval | Lading | Spin | Doublon |
| --- | --- | --- | --- |
| Tegen readout-only | [-0.879, 0.220] | [-0.746, 0.367] | [-0.640, 0.028] |
| Tegen lineaire ZNE | [-0.517, 0.144] | [-0.523, 0.199] | [-0.284, 0.009] |

Alle zes intervallen omvatten 0. Er is dus geen overtuigend opgeloste verbetering.
De brede intervallen bewijzen ook niet dat alle negatieve puntschattingen
een systematische hardwarefout zijn. Het zijn heuristische onzekerheidsintervallen,
geen gegarandeerde frequentistische dekking of p-waarden. Met7 shots kan
empirisch resamplen onbekende zeldzame uitkomsten niet modelleren.

De L-MPF-reconstructie heeft Zu=1.742331 en lokale kansen
`[0.719996, -0.061692, 0.651170, -0.309473]` voor 00/10/01/11.
Dit zijn onfysische **geextrapoleerde schattingen**, niet letterlijk negatieve
kansen die de quantumcomputer heeft uitgegeven. Ze zijn niet afgeknipt,
genormaliseerd of vervangen door bekende controlewaarden. ZNE geeft eveneens
een negatieve doublonschatting.

In de centrale readoutkalibratie zijn voor beide qubits geen flips waargenomen
in 64 shots per voorbereid bit. Dat bewijst geen nulruis. De Jeffreys-posterior
geeft hier 0.007692 voor elk van de vier assignment-errorparameters.
De fixed-calibration-SD van L-MPF is 0.277877/0.282612/0.174115, bijna gelijk aan
de totale bootstrap-SD. Binnen deze onzekerheidsberekening domineert daarom de
targetshotspreiding. Drift, gecorreleerde readout, TN-fouten en een mogelijk
verkeerd device-ruismodel worden door deze intervallen niet afgedekt.
Meer shots kunnen spreiding verlagen, maar bewijzen niet dat modelbias verdwijnt.

## Alle beschikbare targetshots: afzonderlijke secundaire vergelijking

Geen shots zijn uit het archief verwijderd. Met alle 64+7+14=85 targetshots
en dezelfde128 kalibratieshots wordt het totaal213, dus geen gelijk budget
ten opzichte van de primaire readoutbaseline.

| Secundair | Centrale lading | Centrale spin | Centrale doublon |
| --- | ---: | ---: | ---: |
| L-MPF met alle 85 targetshots | -0.062405 | -0.397728 | -0.289152 |
| Bootstrap-SD | 0.262873 | 0.252991 | 0.168379 |

De spinpuntwaarde ligt dan dichter bij exact (absolute fout 0.035706), maar
lading en doublons blijven negatief. Dit gunstigere spinpunt mag niet als
algemene of gematchte-budgetverbetering worden gekozen. De flinke wijziging
tussen subset en alle shots onderstreept de steekproefgevoeligheid.

## Wat is wel gecontroleerd?

- Gewichten komen ongewijzigd uit de geverifieerde normcontrole: chi128 voor
  Z_up/Z_down en chi256 voor ZZ; ridge 1/56. Er is niet op targetwaarden gefit.
- Job, backend, receipt-/planhash, native QPY-bestanden, twirlmaskers, bitvolgorde
  en coefficientherkomst zijn gecontroleerd. Er is geen gemiddelde over acht
  twirls gecombineerd met enkele-twirlgewichten.
- Readout wordt geinverteerd voordat het X-masker wordt teruggedraaid.
  ZZ is het gemiddelde van gecorrigeerde per-shotproducten, niet het product
  van twee afzonderlijke gemiddelden. Identiteitstermen blijven afzonderlijk.
- Alle 45 regressietests slagen. Een onafhankelijke auditor gebruikt een
  expliciete twee-bit assignmentmatrix-inversie, niet de productieformule.
  Hij reconstrueert alle vijf methoden en alle 10,000 bootstrapreplicaties,
  subset/seeds, budgetten, fysieke transformaties en gepaarde intervallen.
- Maximale afwijking tussen beide routes: 2.22e-16 voor centrale fysieke
  puntschattingen en 1.56e-15 voor bootstrap-Pauliwaarden.
- Runfunctie 3.532 s; auditfunctie 0.846 s, exclusief imports/launcher,
  documentatie en Git. Oudere TN-berekeningen blijven deel van de totale
  klassieke voorbereiding. Nieuw QPU-gebruik: 0 seconden.
- Broncode, exacte geselecteerde ruwe bitstrings, subsetindices, gewichten,
  bootstrapcounts, kalibratietrekkingen en resultaten zijn opgeslagen.
  Het bootstrapbestand is 3,062,205 bytes, onder de 10 MB-grens.

## Conclusie en vervolg

De physics-verificatieskill houdt een geslaagde software-/overlapaudit apart
van geslaagde hardwaremitigatie. Deze beperkte hardwarepilot levert geen
betrouwbare verbetering op en geen reden om naar 6x6 te gaan.

We hebben slechts drie centrale operatoren en een enkele twirl getoetst.
Deze vergelijking is bovendien niet dezelfde dataset/samenstelling als de
eerdere chi1-analyse over acht twirls en negen sites. De verschillen mogen dus
niet alleen aan hogere chi worden toegeschreven. Geen quantum-advantageclaim.

Een goedkope volgende stap, voordat nieuwe QPU-tijd wordt gebruikt, is een
afzonderlijke shotafhankelijke regularisatiecontrole op dezelfde data. De hier
bewust bevroren ridge 1/56 legt iedere arm dezelfde coefficientstraf op, terwijl
de aantallen 43/7/14 sterk verschillen. Een nieuwe straf gebaseerd op vooraf
vastgelegde shotvarianties of bovengrenzen kan de spreiding anders afwegen.
Die aanpak moet voor de vergelijking worden vastgelegd, zonder tuning op de
exacte doelwaarden. Het is een voorstel, geen in deze pilot geteste verbetering
of bewijs dat uitsluitend de regularisatie het slechte resultaat veroorzaakt.

De prioriteit ligt nu bij het toetsen van het ruismodel en beter bemonsteren
van de gevouwen armen op 3x3, niet automatisch bij hogere chi of een groter
rooster. De beschikbare data scheiden shotruis en modelbias niet betrouwbaar.
Een nieuwe hardwarejob vereist apart, vers akkoord op backend, shots en tijd.

## Reproduceren en bewijsbestanden

In de bestaande WSL-Qiskitomgeving, vanuit de repository, met een nieuwe map:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B lmpf_2d/single_twirl.py --output NEW_DIRECTORY
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B lmpf_2d/verify_single_twirl.py NEW_DIRECTORY
```

- [Protocol en budgetten](plan.json), [frozen weights en subsets](frozen_weights.json).
- [Geselecteerde bronmetingen](selected_inputs.json), [volledige resultaten](summary.json).
- [Onafhankelijke audit](verification/verification.json), [verificatienotitie](VERIFICATION.md).
- [Hashmanifest](sha256.json); alle bootstraparrays staan in `bootstrap.npz`.
- [Voorafgaande normcontrole](../lmpf_3x3_exact_norm_2026-09-09_v1/DELIVERY.md).

Geen installatie, verwijdering van oude resultaten, GitHub-push of publicatie.
