# Hogere-chi-controle: nog geen stabiele L-MPF-coefficiënten

8 september 2026. De gevraagde offline chi=2/4-controle is uitgevoerd op de
werkelijke opgeslagen 3x3-circuits. Omdat deze niet convergeert, is ook een
begrensde chi=8/16-diagnose uitgevoerd. **Geen nieuwe hardwarejob, geen nieuwe
volledige 3x3-mitigatietabel en geen 6x6-berekening.**

## Afbakening

Job `daem7r642tqs73autong`, `ibm_phoenix`, 18 actieve draden, U8, T0.4,
twee symmetrische stappen. Geselecteerd vóór uitvoering: centrale Z_up,
Z_down en onsite ZZ (indices 8,9,22), vaste twirl 0, ideale arm en werkelijke
CZ-foldingfactoren 1/2/3. De vaste ridge bleef 1/56. Geen doelwaarde of gemeten
hardwaregemiddelde is gebruikt om coëfficiënten te fitten.

Dit zijn drie operatorcontroles, niet de volledige 27-observable/acht-twirl-
schatting. De nieuwe één-twirlcoëfficiënten zijn niet op de acht-twirlmetingen
toegepast. Het eerdere hardware-no-go-resultaat blijft ongewijzigd.

## Belangrijk topologisch inzicht

Het fysieke Hubbard-model is tweedimensionaal, maar de gebruikte native
poortverbindingen in deze drie circuits vormen de keten 0-1-...-17: 18 knopen,
17 verbindingen, geen lussen. De koppelingen zijn expliciet uit alle drie
opgeslagen circuits uitgelezen. **De 2D-fysica en de native circuitgraaf zijn
niet hetzelfde.** Loopcorrecties hebben op deze keten geen niet-triviale rol.

De eerder uitgevoerde acht-qubitpilot gebruikte wel een ladder met lussen.
De nieuwe hogere-chi-controle op de hardwarecircuits mag dus niet worden
voorgesteld als een nieuwe validatie van de volledige 2D-loopmethode uit de paper.

## Stabiliteit van de overlaps en coëfficiënten

Vooraf vastgelegde noodzakelijke vlaggen: relatieve Frobenius-verandering van
de volledige Gram-matrix <=1%, en absolute L1-verandering van de vaste-ridge-
coëfficiënten <=0.05. Ook slagen zou nog geen volledig convergentiebewijs zijn.

| Centrale operator | Gramverandering chi2 naar chi4 (D2BP) | L1-coëfficiëntverandering | Vlag |
| --- | ---: | ---: | --- |
| Z_up | 9.825% | 0.31418 | Niet geslaagd |
| Z_down | 8.635% | 0.50547 | Niet geslaagd |
| ZZ | 24.838% | 0.85332 | Niet geslaagd |

Een onafhankelijke, gemengd-canonieke MPS-route is vervolgens toegevoegd voor
de geverifieerde ketentopologie. Deze gebruikt geen BP-berichten. Na controles
tegen exacte kleine operatoren en de bestaande chi=1-route is chi=4/8/16
doorgerekend op dezelfde drie observabelen en dezelfde vier armen.

| Centrale operator | Gramverandering chi8 naar chi16 (canonieke MPS) | L1-coëfficiëntverandering | Vlag |
| --- | ---: | ---: | --- |
| Z_up | 8.688% | 0.32507 | Niet geslaagd |
| Z_down | 6.826% | 0.37850 | Niet geslaagd |
| ZZ | 29.696% | 0.79378 | Niet geslaagd |

De grotere chi is dus nog geen stabiele invoer voor L-MPF. Dit is iets anders
dan zeggen dat meer shots niet kunnen helpen: meer shots verminderen de
samplingruis, maar tonen geen convergentie van de klassieke overlaps aan.

## Truncatie versus contractie

De exacte contractie van de opgeslagen lage-chi-netwerken en de BP/loop-
contractie stemmen op deze keten overeen binnen numerieke afronding. De
gevoeligheid bij veranderende chi komt dus niet van een verschil tussen die
twee eindcontracties. Truncatie tijdens de operatorpropagatie blijft essentieel.

Ter illustratie staan hieronder de puur klassieke ideale TN-verwachtingswaarden.
Dit zijn **geen nieuwe gemitigeerde hardwaremetingen**. Een TN-verwachting hoeft
voor L-MPF niet exact te zijn; daarom wordt de overlap-/coëfficiëntstabiliteit
apart getoetst en niet vervangen door deze tabel.

| Operator | Exact eindig circuit | chi1 D2BP/product | chi2 D2BP | chi4 canonieke MPS | chi8 canonieke MPS | chi16 canonieke MPS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Z_up | 0.957351 | 0.843438 | 0.766595 | 0.604079 | 0.799300 | 0.923776 |
| Z_down | 0.233308 | 0.843438 | 0.756313 | 0.605825 | 0.442579 | 0.226213 |
| ZZ | 0.229400 | 0.711388 | 0.571920 | 0.427900 | 0.407509 | 0.163943 |

Ook de twee propagatieroutes zijn niet overal identiek bij kleine chi. Voor
Z_up op chi2 zijn de gecontroleerde ideale en factor-1-operatoren gelijk
binnen afronding. Op chi4 geldt dat voor de factor-1-operator, maar de ideale
operator verschilt ongeveer 3.99% in relatieve HS-norm, ondanks vrijwel gelijke
norm en deze ene verwachtingswaarde. Bij ZZ verschilt de chi4-ideale verwachting:
D2BP 0.413734, canonieke MPS 0.427900. Dit blijft zichtbaar; zonder nadere
analyse schrijven we dit niet stellig toe aan één specifieke oorzaak.

## Verificatie en rekentijd

- D2BP chi=1/2/4-diagnose: 29 regressietests, circa 505.974 s.
- Extra canonieke chi=4/8/16-diagnose: 31 regressietests, circa 26.457 s.
- Beide tijden zijn gemeten binnen de runfunctie, exclusief imports en launcher.
- Dit zijn verschillende rekenpakketten en geen matched-accuracy-snelheidsbenchmark.
  Er volgt geen quantum-advantageclaim uit deze lokale tijden.
- Onafhankelijke audits hercontracteren de tensors in omgekeerde volgorde,
  controleren bron-/datahashes, coefficientnormalisatie, PSD, optimaliteit,
  projectieresidu en de stabiliteitsclassificatie.
- Maximale Gramreconstructieafwijking: D2BP 2.78e-16, canonieke verfijning 1.12e-15.
- 36 fits gecontroleerd in de D2BP-audit, 18 in de canonieke audit.
- Alle numerieke data, indices, tags en exponenten zijn opgeslagen; geen pickle.
- De ontwikkelrun v1 is bewust gestopt wegens een fout in de statuspredicate,
  die geldige fits ten onrechte als ontbrekend kon markeren. De fout is
  hersteld en heeft een regressietest; de gedeeltelijke v1-data zijn behouden.

## Volgende inhoudelijke stap

De ketenroute maakt een verdere chi=32/64-controle uitvoerbaar. Daarna zijn
nog de volledige 27 observabelen, alle acht twirls, een onafhankelijk getoetst
ruismodel en opnieuw de 3x3-kwaliteitscontrole nodig. Pas daarna is er een
onderbouwde basis voor een nieuwe hardware-run; die vereist een nieuw budget.
Deze controles zijn in deze stap niet als voltooid aangemerkt.

Volgens de physics-verificatieskill blijven onstabiele coëfficiënten buiten
vervolgclaims. Meer shots of een beter totaal N mag de mislukte controle niet
verbergen. De eerdere 6x6-voorwaarde is niet opgeheven.

## Bestanden

- [Plan](plan.json), [stabiliteitsuitkomst](summary.json), [hashmanifest](sha256.json).
- [Onafhankelijke audit](verification/verification.json).
- [Canonieke cross-check](canonical_crosscheck/summary.json).
- [Extra chi8/16-uitkomst](../lmpf_3x3_canonical_refine_2026-09-08_v1/summary.json).
- [Audit extra verfijning](../lmpf_3x3_canonical_refine_2026-09-08_v1/verification/verification.json).
- [Eerdere volledige 3x3-hardwaretoepassing](../lmpf_3x3_hardware_2026-09-08_v1/DELIVERY.md).

Uitvoering: bestaande WSL `/home/bram/.venvs/qiskit/bin/python`, één BLAS-thread.
Geen nieuwe packages, QPU-job, GitHub-push of publicatie.

```sh
python -B lmpf_2d/higher_bond.py --output NEW_DIAGNOSTIC --budget-seconds 1200
python -B lmpf_2d/canonical_chain.py NEW_DIAGNOSTIC
python -B lmpf_2d/canonical_refine.py --output NEW_REFINEMENT
python -B lmpf_2d/verify_higher_bond.py NEW_DIAGNOSTIC
python -B lmpf_2d/verify_higher_bond.py NEW_REFINEMENT
```
