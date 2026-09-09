# ZZ chi256: coefficienten stabiel, volledige Gram-test nog net onvoldoende

9 september 2026. Alleen de centrale ZZ-operator (Z8 Z9, index22) is opnieuw
gepropageerd, met chi256, twirl0 en vier armen: ideaal en werkelijke CZ-folding
1/2/3 van het opgeslagen 3x3-job `daem7r642tqs73autong` op `ibm_phoenix`.
Chi128 is byte-voor-byte hergebruikt. **Geen nieuwe QPU-job, hardwaregewichten
of 6x6-run.** De eerdere Z_up/Z_down-resultaten op chi128 zijn niet herberekend.

## Vooraf vastgelegde controles

| ZZ-controle | chi64->128 | chi128->256 | Grens | Nieuw oordeel |
| --- | ---: | ---: | ---: | --- |
| Relatieve volledige Gram-verandering | 3.2948% | 1.3098% | <=1% | niet geslaagd |
| L1-verandering vaste-ridgecoefficienten | 0.083241 | 0.032187 | <=0.05 | geslaagd |

Beide voorwaarden moeten gelden. De gewichten zijn nu lokaal stabiel volgens
de coefficientengrens, maar de gezamenlijke test blijft onvoldoende. Dit zijn
convergentiediagnoses, geen gemeten hardwarefouten of rigoureuze foutgrenzen.
De grenzen en ridge 1/56 zijn niet na de berekening aangepast.

Nieuwe ridgegewichten voor armen 1/2/3:
`[2.617390439989012, -0.2072591770700905, -1.4101312629189222]`.
Ze sommeren tot 1 binnen afronding. Negatieve gewichten zijn behouden; er is
geen target- of hardwaregemiddelde gebruikt in de fit. De onregulariseerde
gewichten hebben L1-norm40.979, tegenover 4.235 voor ridge, en blijven afzonderlijk
zichtbaar in de JSON. Geen achteraf gekozen gunstigste estimator.

## Belangrijke tegencontrole: de ideale ZZ-verwachting is niet beter geworden

| Grootheid | Exact eindig circuit | chi128 | chi256 |
| --- | ---: | ---: | ---: |
| Ideale ZZ-verwachting | 0.229400442 | 0.223030783 | 0.237676227 |
| Absolute afwijking tegenover exact | 0 | 0.006369659 | 0.008275785 |

Chi256 overschiet de referentie. De fout van deze afzonderlijke verwachting
neemt dus toe, ondanks de afnemende overlap- en coefficientenverandering.
Een kleinere HS/Gram-verandering impliceert geen monotone verbetering van
iedere toestandsspecifieke verwachting. Er is geen monotone trend of
extrapolatie naar oneindige chi aangenomen. De onafhankelijke reconstructie
bevestigt de opgeslagen getallen; de gegevens bewijzen geen algemene
nauwkeurigheidswinst en identificeren op zichzelf geen fout in de code.

Deze referentie is die van het eindige ideale circuit, niet van exacte
Hamiltoniaanevolutie zonder productformulefout. Dit zijn klassieke TN-waarden,
geen nieuwe hardwarewaarden voor lading, spin of doublons.

## Nacontrole: welk onderdeel veroorzaakt de resterende Gram-verandering?

Deze uitsplitsing is achteraf uitgevoerd om de oorzaak te begrijpen, niet om
de acceptatieregels te vervangen. F is de vier-bij-vier Gram, met ideale arm 0,
b=F[0,1:] en G=F[1:,1:].

| Component | chi128->256 |
| --- | ---: |
| G: relatieve ruis-ruisoverlapverandering | 0.1311% |
| b: relatieve ideaal-ruisoverlapverandering | 0.4988% |
| Aandeel F00 in de som van gekwadrateerde veranderingen | 98.0851% |

F00 stijgt van 0.979988040 naar0.993886268. Voor de exacte ideale Pauli-operator
O=Z8 Z9 en een unitaire U geldt echter algebraisch:

```text
O^2 = I
Tr[(U_dagger O U)^2] / 2^18 = Tr[U_dagger O^2 U] / 2^18 = 1.
```

De ideale normterm is dus exact bekend. Hij is bovendien constant ten opzichte
van de coefficienten in de kwadratische fit: de optimizer hangt van G en b af.
Dit verklaart waarom de coefficientenvlag al kan slagen terwijl de volledige
Gram-vlag nog faalt. We hebben F00 hier niet vervangen, geen fits gewijzigd
en geen nieuwe geslaagde beoordeling geconstrueerd. Het 98%-getal slaat op de
**gekwadrateerde Frobenius-verandering**, niet op98% van een hardwarefout.

Een volgende goedkope stap kan deze exacte normalisatie expliciet toetsen
en vooraf vastleggen hoe de nog benaderde G/b-blokken worden beoordeeld.
Dat is gerichter dan automatisch naar chi512 gaan. Ook zo'n aangepaste
toekomstige controle zou geen rigoureuze G/b-foutgrens, gevalideerd ruismodel
of volledige hardware-kwaliteitsvergelijking vervangen.

## Rekengrenzen en tijd

Het 2D-Hubbard-model en de native open keten van 18 actieve wires zijn gelijk
gebleven. De bestaande canonieke propagatiekern, cutoff 1e-12, tekenconventies,
fysieke voorbereidingspoorten en lokale depolarisatiesurrogaat zijn ongewijzigd.

De analytische chi256-resourcecontrole gaf maximaal 2,769,572,160 geschatte
rekenoperaties per ketenoverlap; het oude 2e9-plafond was daarvoor te laag.
Alleen de nieuwe driver en auditor gebruiken daarom het vooraf vastgelegde
3e9-plafond. Het geheugenplafond voor contractie blijft 2^22 elementen.
De grootste daadwerkelijk gecontracteerde tussenarray telt 262,144 elementen.
Er is geen dichte 4^18-operator of lokale chi^4-bra/ket-array aangelegd.

| Uitvoering | Gemeten seconden |
| --- | ---: |
| Ideale arm 0, inclusief opslaan en norm-roundtrip | 181.564 |
| Ruisarm 1 | 177.782 |
| Ruisarm 2 | 180.471 |
| Ruisarm 3 | 171.648 |
| Volledige runfunctie | 724.851 |
| Onafhankelijke auditfunctie | 8.980 |

De run duurde ongeveer 12.1 min en bleef onder de zachte 1500 s-limiet, gecontroleerd
tussen toestanden. Proces-piek-RSS:568,713,216 bytes, ongeveer 542 MiB, onder 2 GiB.
Imports en WSL-launcher vallen buiten de functietimers. Archiveren, menselijk
nakijken en Git vallen daar ook buiten. Dit is klassieke mitigatievoorbereiding,
geen nieuwe end-to-end-, matched-accuracy- of quantum-advantagebenchmark.
Nieuw QPU-gebruik: 0 seconden.

## Verificatie en behoud van alle gegevens

- Alle 36 tests zijn geslaagd: de eerdere33 plus resource-, split-archive- en
  veilige hersteltests. Een afwijkend bestaand bestand wordt niet overschreven.
- De parent-checksums, kalibratie, native QPY-inputs, broncode en opgeslagen
  tensorarrays zijn gecontroleerd.
- De onafhankelijke ruwe-TN-contractie reconstrueert alle Grams en vier fits.
  Maximale Gram-afwijking: 1.33227e-15; geprojecteerde fitgradient: 9.94755e-17;
  afwijking in gereconstrueerde ideale verwachting: 4.16334e-16.
- Alle vier grote NPZ-originelen blijven lokaal in `states/`, ongeveer
  15.9-16.9 MB per bestand. Ze worden niet rechtstreeks in Git gezet.
- Dezelfde bytes zijn bewaard in acht SHA256-gecontroleerde gzip-delen, elk
  maximaal 9,000,000 bytes, onder het resultaatlokale `archive/objects/`.
  De bestaande onafhankelijke streaming-restorer verifieerde alle vier objecten
  en de aanwezige originelen. Niets is verwijderd of overschreven.
- De nieuwe nacontrole heeft een eigen input-/bronhash en wijzigt de oorspronkelijke
  `observable_22.json`, fits, vlaggen of het numerieke manifest niet.

De physics-verificatieskill houdt software-/bewijsverificatie en natuurkundige
convergentie apart. De gezamenlijke ZZ-controle is nog niet geslaagd. De verdere
voorwaarden blijven open: alle 27 observabelen, acht twirls en hun kruistermen,
device-noise-validatie, projectiebias en shot-/kalibratieonzekerheid.
De eerdere 3x3-hardware-no-go voor lading/doublons blijft staan; geen 6x6.

## Bestanden en reproduceren

- [Plan](plan.json), [samenvatting](summary.json), [numeriek hashmanifest](sha256.json).
- [Onafhankelijke audit](verification/verification.json) en [verificatienotitie](VERIFICATION.md).
- [Volledige operatorgegevens](observable_22.json), [componentdiagnose](component_diagnostics.json).
- [Archiefmanifest](archive/manifest.json), [archiefcontrole](archive/verification.json).
- [Voorgaande chi128-stap](../lmpf_3x3_chi128_2026-09-08_v1/DELIVERY.md).

In de bestaande WSL-Qiskitomgeving, vanuit de repository:
```sh
# Na clonen: herstel alleen de vier grote resultaatbestanden, zonder overschrijven.
python -B lmpf_2d/portable_archive.py restore results_cuprate_2d/lmpf_3x3_zz_chi256_2026-09-09_v1

# Een nieuwe berekening en onafhankelijke verificatie: gebruik een nieuwe map.
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B lmpf_2d/canonical_chi256.py --output NEW_DIRECTORY
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B lmpf_2d/verify_zz_chi256.py NEW_DIRECTORY
python -B lmpf_2d/portable_archive.py pack NEW_DIRECTORY
python -B lmpf_2d/diagnose_zz_refinement.py NEW_DIRECTORY
```

Bij een verse clone moeten ook de oorspronkelijke QPY-inputs beschikbaar zijn;
daarvoor blijft de bestaande repository-restorer van toepassing. Bewaarde audit-
en diagnoserapporten worden niet overschreven bij herhaald uitvoeren.
Geen installatie, GitHub-push of publicatie.
