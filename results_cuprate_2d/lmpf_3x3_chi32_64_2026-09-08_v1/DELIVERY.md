# Chi32/64: duidelijke convergentietrend, nog geen geslaagde stabiliteitscontrole

8 september 2026. De volgende offline stap is uitgevoerd op dezelfde drie
centrale 3x3-observabelen: Z_up, Z_down en onsite ZZ, één vaste twirl (0), de
ideale arm en de drie werkelijke CZ-foldingarmen. Job `daem7r642tqs73autong`,
`ibm_phoenix`. **Geen nieuwe QPU-job, geen nieuwe volledige hardwaretabel en
geen 6x6-berekening.**

## Overlapstabiliteit

Onderstaande percentages zijn veranderingen van de volledige overlap-Gram-
matrix bij het verhogen van chi, niet fouten in hardwaremetingen of bewezen
afwijkingen tegenover de exact bekende Gram-matrix.

| Centrale operator | chi16 naar chi32 | chi32 naar chi64 | Vereiste grens |
| --- | ---: | ---: | ---: |
| Z_up | 3.5734% | 1.7262% | <=1% |
| Z_down | 2.9782% | 1.3645% | <=1% |
| ZZ, nodig voor doublons | 15.7494% | 7.0731% | <=1% |

De verschillen worden duidelijk kleiner. Z_up en Z_down naderen de gekozen
grens, maar halen die nog niet. De ZZ-overlaps zijn nog duidelijk gevoeliger.

Ook de tweede, vooraf vastgelegde controle slaagt nog niet:

| Operator | L1-verandering ridge-coëfficiënten, chi32 naar chi64 | Vereiste grens |
| --- | ---: | ---: |
| Z_up | 0.063260 | <=0.05 |
| Z_down | 0.065368 | <=0.05 |
| ZZ | 0.216421 | <=0.05 |

Deze noodzakelijke numerieke vlaggen zijn geen universele natuurkundige
drempels en ook geen foutcertificaat. Ze zijn niet achteraf versoepeld om deze
run te laten slagen. Ridge blijft 1/56; doelwaarden en hardwaregemiddelden
zijn niet gebruikt om de coëfficiënten te fitten.

## Klassieke ideale verwachtingen als aanvullende controle

Dit zijn uitsluitend TN-verwachtingen voor de ideale eindige circuits, niet
nieuwe gemitigeerde QPU-resultaten. L-MPF vereist niet dat de klassieke TN de
verwachting zelf exact berekent; overlapstabiliteit wordt daarom apart beoordeeld.

| Operator | Exact eindig circuit | chi16 | chi32 | chi64 |
| --- | ---: | ---: | ---: | ---: |
| Z_up | 0.957351 | 0.923776 | 0.937213 | 0.943552 |
| Z_down | 0.233308 | 0.226213 | 0.202337 | 0.230025 |
| ZZ | 0.229400 | 0.163943 | 0.189544 | 0.214942 |

De chi64-verwachtingen liggen dichter bij de referentie dan chi32, maar dat
vervangt de mislukte overlap-/coëfficiëntcontrole niet. Er is geen extrapolatie
naar oneindige chi uitgevoerd en geen uitspraak over alle negen lattice-sites.

## Uitvoering en onafhankelijke verificatie

- Chi16 is byte-voor-byte hergebruikt uit de eerdere gecontroleerde canonieke
  verfijning. Alle nieuwe chi32/64-operatoren zijn vanaf de oorspronkelijke
  inputoperator en volledige native gatevolgorde gepropageerd.
- Het 2D-Hubbard-model blijft ongewijzigd; de gebruikte native poortgraaf is
  de eerder geverifieerde open keten met 18 knopen en 17 verbindingen.
- Een exacte ketenomgevingscontractie vermijdt onnodige lokale chi^4 bra/ket-
  objecten. De onafhankelijke audit gebruikt de ruwe tensor-netwerken en een
  andere contractievolgorde, zonder die site-voorcontractie.
- 33 regressietests geslaagd: inclusief exacte kleine operatoren, native-keten-
  aannames, chi1-limiet, tensoropslag, solver en beide contractiemethoden.
- Alle 18 unregularized/ridge-fits van chi16/32/64 zijn onafhankelijk geaudit.
  Maximale overlapreconstructieafwijking: 2.34e-15; maximale geprojecteerde
  optimizergradiënt: 3.71e-16; verwachtingsreconstructie: 7.78e-16.
- Grootste tussenobject in de onafhankelijke audit: 16,384 elementen,
  ruim onder de 2^22-grens. Geen dichte 4^18-operator is aangelegd.
- De berekening duurde 131.399 s, de audit 7.904 s, gemeten in de runfuncties
  exclusief imports/launcher. Dit is een andere taak dan de historische
  6x6-classical/QPU-timingvergelijking; geen nieuwe snelheids- of advantageclaim.

## Conclusie en vervolg

De ketenroute werkt en de convergentietrend is beter, maar chi64 voldoet nog
niet aan de vaste criteria. Daarom zijn deze één-twirlcoëfficiënten niet op
de volledige acht-twirlmetingen toegepast. De eerdere 3x3-hardware-no-go blijft
staan; de physics-verificatieskill verhindert dat een niet-geconvergeerde
tussenstap als gevalideerde hardwaremitigatie wordt doorgeschoven.

Een volgende begrensde stap is chi128, met extra aandacht voor ZZ. Daarna
blijven de volledige 27 observabelen, alle acht twirls, onafhankelijk getoetste
device-noise en de werkelijke 3x3-kwaliteitsvergelijking nodig. Geen nieuwe
hardware-uitvoering zonder expliciet nieuw budget.

## Bewijsbestanden en reproduceerbaarheid

- [Plan](plan.json), [samenvatting](summary.json), [hashmanifest](sha256.json).
- [Onafhankelijke audit](verification/verification.json).
- Per-operator JSONs bevatten de volledige Grams, coëfficiënten, spectra,
  conditionering, waarden en timings. Tensorarrays plus index/tag/exponent-
  metadata staan onder `states/`, zonder pickle.
- [Eerdere chi2/4 en chi8/16-stap](../lmpf_3x3_higher_bond_2026-09-08_v2/DELIVERY.md).

Gebruik de bestaande WSL-omgeving `/home/bram/.venvs/qiskit`:

```sh
python -B test_lmpf_chain_contract.py
python -B lmpf_2d/canonical_extend.py --output NEW_DIRECTORY
python -B lmpf_2d/verify_higher_bond.py NEW_DIRECTORY
```

Alle eerdere gegevens zijn behouden. Geen installatie, GitHub-push of publicatie.
