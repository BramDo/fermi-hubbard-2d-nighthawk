# Chi128: beide Z-operatoren lokaal stabiel, ZZ nog niet

8 september 2026. De afgesproken offline 3x3-vervolgstap is uitgevoerd.
Dezelfde centrale operatoren (8,9,22), twirl 0, ideale arm en drie werkelijke
CZ-foldingarmen van job `daem7r642tqs73autong` op `ibm_phoenix` zijn gebruikt.
**Geen nieuwe QPU-job, geen nieuwe volledige hardwaretabel en geen 6x6-run.**

## Ongewijzigde stabiliteitscontrole

Deze percentages zijn relatieve veranderingen van de volledige overlap-Gram-
matrix bij verdubbeling van chi. Het zijn geen hardwarefouten en geen bewezen
afwijkingen van de exacte Gram-matrix. Beide criteria moeten per operator slagen.

| Centrale operator | Gram chi32->64 | Gram chi64->128 | Coefficient-L1 chi64->128 | Lokale vlaggen |
| --- | ---: | ---: | ---: | --- |
| Z_up | 1.7262% | 0.3639% | 0.012577 | beide geslaagd |
| Z_down | 1.3645% | 0.2962% | 0.013187 | beide geslaagd |
| ZZ, nodig voor doublons | 7.0731% | 3.2948% | 0.083241 | beide mislukt |
| Vooraf vastgelegde grens | <=1% | <=1% | <=0.05 | |

De Gram-verandering van ZZ is opnieuw ruim gehalveerd, maar blijft boven 1%.
De twee enkelvoudige Z-operatoren halen nu wel de noodzakelijke numerieke
stabiliteitsvlaggen. Dit is vooruitgang voor het bepalen van mitigatiegewichten,
niet het bewijs dat de lading-, spin- of doublonmetingen al beter zijn geworden.
De criteria zijn niet achteraf aangepast en zijn geen rigoureuze foutgrenzen.

De vaste ridge blijft 1/56. De chi128-coefficienten (armen 1,2,3) zijn:

| Operator | c1 | c2 | c3 |
| --- | ---: | ---: | ---: |
| Z_up | 2.172338 | 0.023164 | -1.195502 |
| Z_down | 1.893877 | 0.024016 | -0.917893 |
| ZZ | 2.601297 | -0.197905 | -1.403392 |

Elke rij sommeert tot 1 op afronding na. Negatieve gewichten zijn behouden.
Doelwaarde en hardwaregemiddelden zijn niet gebruikt bij de fit. Ook de
onregulariseerde fits, spectra, conditionering en projectieresiduen staan in
de per-operator JSONs; er is geen selectie van de gunstigste fit achteraf.
Stabiele gewichten elimineren niet automatisch projectie- of shotfouten.

## Klassieke ideale verwachtingen: aparte controle

Dit zijn TN-verwachtingen van de ideale eindige circuits, geen gemitigeerde
hardwaremetingen. De referentie betreft het eindige circuit, niet de exacte
Hamiltoniaanevolutie zonder productformulefout.

| Operator | Exact eindig circuit | chi64 | chi128 | Absolute afwijking chi128 |
| --- | ---: | ---: | ---: | ---: |
| Z_up | 0.957350560 | 0.943552222 | 0.956628775 | 0.000721785 |
| Z_down | 0.233308190 | 0.230025266 | 0.235773731 | 0.002465542 |
| ZZ | 0.229400442 | 0.214941513 | 0.223030783 | 0.006369659 |

Alle drie absolute afwijkingen zijn kleiner dan bij chi64. Z_down ligt nu
boven de referentie, waar chi64 eronder lag. De waarden convergeren dus niet
eenzijdig; er is geen extrapolatie naar oneindige chi uitgevoerd. De exacte
verwachtingen dienen alleen als controle: L-MPF fit hier operatoroverlaps.

## Reproduceerbaarheid en audit

- Chi64 is byte-voor-byte gekopieerd uit de eerdere gecontroleerde run.
  Het volledige parent-hashmanifest, de kalibratie en de native QPY-inputs
  zijn gecontroleerd. Alle twaalf nieuwe chi128-netwerken zijn vanaf de
  oorspronkelijke operator en volledige native gatevolgorde berekend.
- Het Hubbard-model is 2D; de native poortgraaf is de geverifieerde open keten
  van 18 actieve wires. De bestaande canonieke MPS-kern is ongewijzigd.
- Overlaps zijn exact gecontraheerd voor de opgeslagen, getrunceerde MPS.
  Een onafhankelijke ruwe-TN-contractie met andere tensorvolgorde reconstrueert
  de Grams. Er is geen dichte 4^18-operator aangelegd.
- Alle 33 regressietests zijn geslaagd. De audit controleert alle twaalf
  unregularized/ridge-fits van chi64/128, inclusief PSD, normalisatie,
  stationariteit, projectieresidu en onafhankelijke stabiliteitsclassificatie.
- Maximale Gram-reconstructieafwijking: 2.33147e-15. Maximale geprojecteerde
  optimizergradient: 3.70092e-16. Verwachtingsreconstructie: 7.77156e-16.
  Grootste audit-tussenobject: 65,536 elementen, onder de 2^22-grens.
- De runfunctie duurde 474.575 s (ongeveer 7.9 min), de audit 6.516 s,
  exclusief Python-imports en WSL-launcher. De 900 s-limiet werd niet bereikt.
  Dit is extra klassieke mitigatievoorbereiding; niet dezelfde taak of klok
  als de historische 6x6-vergelijking van 150 s met 7/8 QPU s.
- Alle tensorarrays, metadata, Grams, fits, broncode en tests blijven bewaard.
  Geen individueel bestand is 10 MB of groter; grootste NPZ: 5,698,223 bytes.

## Grenzen en volgende gerichte stap

Software- en bewijsverificatie slagen; de gezamenlijke lokale convergentiepoort
niet. De physics-verificatieskill houdt daarom de doorgang naar gevalideerde
hardwaremitigatie en 6x6 tegen. Drie centrale operatoren van een enkele twirl
zijn niet hetzelfde als alle 27 observabelen en acht twirls, inclusief hun
kruistermen. Deze gewichten zijn niet op de acht-twirlgemiddelden toegepast.

Het kalibratie-afgeleide lokale depolarisatiemodel is nog geen geleerd of
onafhankelijk gevalideerd device-Lindbladmodel. TN-truncatie, modelbias en
shot-/kalibratieonzekerheid blijven afzonderlijke problemen; deze deterministische
run meet geen nieuwe hardware-shotonzekerheid. De oorspronkelijke 3x3-no-go
wegens verslechterde lading/doublons blijft dus staan.

Een volgende begrensde stap kan de ZZ-operator afzonderlijk verder verfijnen
naar chi256. Daarvoor moeten rekentijd, contractiekosten en grotere opslag
vooraf opnieuw worden beoordeeld; het huidige resourceplafond wordt niet stil
verhoogd. Ook succes daarvan vervangt geen volledige twirl-/profielvalidatie.
Geen nieuwe hardwarejob zonder expliciet nieuw backend-/shot-/tijdbudget.

## Bestanden en opnieuw uitvoeren

- [Plan](plan.json), [samenvatting](summary.json), [hashmanifest](sha256.json).
- [Onafhankelijke audit](verification/verification.json), [verificatienotitie](VERIFICATION.md).
- Volledige numerieke gegevens: `observable_08.json`, `observable_09.json`,
  `observable_22.json`; tensorarrays en index/tag/exponent-metadata: `states/`.
- [Voorgaande chi32/64-stap](../lmpf_3x3_chi32_64_2026-09-08_v1/DELIVERY.md).

In de bestaande WSL-omgeving `/home/bram/.venvs/qiskit`, met een nieuwe uitvoermap:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B lmpf_2d/canonical_chi128.py --output NEW_DIRECTORY
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B lmpf_2d/verify_higher_bond.py NEW_DIRECTORY
```

Geen installatie, GitHub-push, publicatie of wijziging van oude resultaten.
