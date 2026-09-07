# qDRIFT: eerste lokale schatting en exact kleine-systeemproef

Geen extra package nodig: QDrift zit in de gebruikte Qiskit 2.5.2. Geen installatie of QPU-run uitgevoerd.
Het aantal willekeurige evolutiestappen N is niet hetzelfde als Qiskit reps of het aantal meetshots.
De eigen expliciet-N sampler is tegen de geinstalleerde QDrift gecontroleerd; zes tests slagen.

## 6x6 circuitresources: voorbeelden, geen nauwkeurigheidsbewijs

Volledig t=1, t-prime=-0.25, U=8, mu=0, T=0.4; 72 modes, 32 deeltjes. Alle Hamiltoniaantermen blijven in de samplingverdeling.
Per kort circuit worden willekeurige termen gekozen; elke afzonderlijke term hoeft daarin niet voor te komen.
Zelfde opgeslagen Nighthawk-kalibratie en Bonsai XYZ/count-rectangle. Een vaste seed, voorbereiding, controle-twirl en uitlezing inbegrepen.
CZ-basis; geen native RZZ aangenomen. De assignment is niet opnieuw voor qDRIFT geoptimaliseerd.

| Variant | N random stappen | CZ | CZ-lagen | Totale diepte | Duur (us) |
|---|---:|---:|---:|---:|---:|
| Bestaand compact twee-stappencircuit | - | 15400 | 564 | 2030 | 72.252 |
| pauli | 128 | 571 | 125 | 414 | 15.788 |
| pauli | 256 | 1362 | 291 | 959 | 34.756 |
| pauli | 512 | 2683 | 567 | 1870 | 66.364 |
| pauli | 1024 | 5208 | 1107 | 3670 | 128.736 |
| grouped | 128 | 1383 | 275 | 956 | 34.048 |
| grouped | 256 | 2776 | 635 | 2178 | 75.220 |
| grouped | 512 | 5618 | 1339 | 4545 | 154.852 |
| grouped | 1024 | 11559 | 2787 | 9444 | 319.424 |

Geschatte onafgeronde kritieke circuitduur, niet de gefactureerde QPU-tijd: geen reset, rep_delay, queue of volledige ZNE/kalibratiebatch.
Resources van een sample voorspellen geen kwaliteitswinst. Minder hardwarefout kan worden ingeruild voor meer qDRIFT-fout.

## Exacte 2x2-proef

Een gat, drie deeltjes, dezelfde t/t-prime/U/T. Referentie is exp(-iHT) in de bezettingsbasis, onafhankelijk opgebouwd en op twee manieren geexponentieerd.
Per rij 256 onafhankelijke noiseless circuits. RMSE over de vier lokale observabelen na middelen over circuits; geen meetshot- of hardwarefout.
Spin is n_up-n_down. De volledige lokale waarden, spreiding, Monte Carlo standaardfouten en resultaten per circuit zijn opgeslagen.

| Variant | N | RMSE lading | RMSE spin | RMSE doublon | Gemiddeld deeltjesaantal | Sectorlekkage |
|---|---:|---:|---:|---:|---:|---:|
| pauli | 16 | 0.254076 | 0.436745 | 0.169986 | 3.724392 | 0.434039 |
| pauli | 32 | 0.173935 | 0.313437 | 0.133505 | 3.513857 | 0.319005 |
| pauli | 64 | 0.099633 | 0.202155 | 0.090694 | 3.309418 | 0.200450 |
| pauli | 128 | 0.057775 | 0.115538 | 0.052745 | 3.163935 | 0.107207 |
| pauli | 256 | 0.030583 | 0.054929 | 0.026257 | 3.090565 | 0.058853 |
| pauli | 512 | 0.014522 | 0.031299 | 0.015086 | 3.045462 | 0.030594 |
| grouped | 16 | 0.111552 | 0.356431 | 0.093651 | 3.000000 | 0.000000 |
| grouped | 32 | 0.089927 | 0.252963 | 0.066880 | 3.000000 | 0.000000 |
| grouped | 64 | 0.057949 | 0.184082 | 0.049183 | 3.000000 | 0.000000 |
| grouped | 128 | 0.037210 | 0.096587 | 0.028241 | 3.000000 | 0.000000 |
| grouped | 256 | 0.017985 | 0.061317 | 0.018977 | 3.000000 | 0.000000 |
| grouped | 512 | 0.010431 | 0.030662 | 0.009076 | 3.000000 | 0.000000 |

Ter vergelijking: het oude twee-stappencircuit op ditzelfde 2x2-systeem heeft tegenover de continue exacte evolutie:
charge RMSE 0.001475, spin RMSE 0.025737, doublon RMSE 0.013508.
Dit is uitsluitend de kleine-systeemvergelijking; oude 6x6 chi64-uitkomsten zijn geen exacte qDRIFT-referentie.

Losse Pauli-qDRIFT behoudt het aantal deeltjes niet per circuit. Gegroepeerde hopping/onsite-qDRIFT doet dat wel, maar kost meer rotaties per random stap.
Meer shots op hetzelfde random circuit verwijderen de algoritmische fout niet; onafhankelijke circuits middelen de random variatie, maar niet de eindige-N kanaalbias.
N is dus een andere knop dan shots. Een goede lading hoeft geen goede spin of doublons te betekenen.

## Schaal en garanties

6x6: Pauli lambda=361 (identity 72 apart), grouped lambda=433. 2x2: Pauli lambda=33, grouped lambda=41.
De random rotatiehoek is lambda*T/N. Hetzelfde N is op 6x6 dus geen vergelijkbare benaderingsnauwkeurigheid.
Qiskit reps=1 zou voor de 6x6 Pauli-decompositie al 41703 random Pauli-rotaties kiezen.
Conservatieve leidende-orde referentieschaal N~2(lambda*T)^2/epsilon: Pauli epsilon=0.1 geeft circa 417,028 stappen.
Dit is geen praktische ondergrens, geen scherpe eindige-N garantie en geen bewijs dat lokale observabelen zoveel nodig hebben.
Normalisatiekanttekening: arXiv:2506.17199 Theorem 1 gebruikt E(T/r)^(r Gamma). Het aantal feitelijke kanaaltoepassingen is r*Gamma; r mag niet direct als fysiek aantal random poorten N worden gebruikt.
Daarom wordt de lineaire-lambda interpretatie uit Boston Appendix B hier niet als hardware-garantie toegepast.

## Oordeel en vervolg

qDRIFT levert een instelbare diepte/benaderingsfout-afruil, geen automatische verbetering door een package.
Nog geen 6x6 noiseless/noisy nauwkeurigheidsvalidatie, aangepaste Bonsai readoutmitigatie, volledige ZNE-batch of hardwaremeting.
Een eventuele vervolgkeuze moet deeltjesbehoud, spin/doublonfout en totaal aantal circuits/shots tegelijk toetsen.
De physics-skill stuurde het vooraf vastleggen van aannames, onafhankelijke teken/nummercontroles en bron/resultaatarchivering.

Bronnen: [Qiskit QDrift](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.synthesis.QDrift), [Campbell](https://arxiv.org/abs/1811.08017), [tighter bounds](https://arxiv.org/html/2506.17199), [Boston](https://arxiv.org/html/2608.25024).
