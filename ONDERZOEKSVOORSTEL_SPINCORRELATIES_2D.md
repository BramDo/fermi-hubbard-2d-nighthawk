# Onderzoeksvoorstel: interactiegevoelige spincorrelaties in 2D

## Vraag en doel

Kan een quantumcomputer de tijdsafhankelijke, verbonden spincorrelaties van
het gedopeerde 2D Hubbard-model binnen een vooraf gekozen foutmarge sneller
berekenen dan goede klassieke methoden op deze pc?

Dit is een onderzoeksvraag, geen vastgestelde quantum advantage. De eerdere
controle kostte slechts 0,114 s rekenen / 1,61 s volledige aanroep en benaderde
de lokale profielen bij een eindpunt goed. Daarom is een nieuwe meetvraag
nodig, niet alleen een groter rooster of hogere chi voor dezelfde vergelijking.

## Model en conventies

Behoud 6x6, 36 sites, 72 spinmodi, 32 deeltjes (16 up / 16 down), vier gaten,
stripe-Neel-begintoestand, open grenzen, t=1, t'=-0.25, U/t=8, mu=0.
Aanvullende kleine validatierung: 3x3, een gat, 4 up / 4 down; ander systeem,
dus een methodetest en geen numerieke vervanging voor 6x6.

Primair m_i=n_i,up-n_i,down. Dit is tweemaal S_z; correlaties van m zijn
viermaal correlaties van S_z. Fysische tijd T in hbar/t-eenheden is geen
computerwandtijd. T=0.4, twee stappen van dt=0.2 is de bestaande circuitanker.

Meetvraag: C_ij(T)=<m_i m_j>-<m_i><m_j>, voor alle verschillende sites.
Bewaar alle paren. Primaire rapportage: afzonderlijke RMS-afstanden voor
Manhattan-afstanden 1, 2 en 3, plus maximale absolute paarafwijking.
Een over alle afstanden verdunde RMS of een getekend gemiddelde met
wegvallende positieve/negatieve correlaties is geen voldoende succesmaat.

## Eerste afgebakende proef: uitvoeren zonder nieuwe hardware

1. Gebruik de opgeslagen MPS-toestanden bij T=0.4: 3x3 chi16/32/64 en
   6x6 chi32/64 (beide threads1 voor de 6x6-vergelijking). Geen evolutie herhalen.
2. Bereken alle Z_q en Z_q Z_r via expliciete NumPy-transfercontracties.
   Controleer bestaande lokale profielen en norm opnieuw.
3. Bereken een exacte 3x3-statevector van hetzelfde eindige circuit als
   onafhankelijk anker voor de correlaties. Geen 6x6-statevector.
4. Vergelijk met U=0 bij dezelfde T en met de bestaande zes-tijdencontrole
   (0.04,0.08,0.12,0.24,0.32,0.48), zonder aanpassing van tijden of gewichten.
5. Leg vast of de nieuwe meetvraag deze eenvoudige controle onderscheidt,
   en of het verschil groter is dan de waargenomen chi-afhankelijkheid.
   Een verschil chi32->64 is geen gecertificeerde foutgrens.

Voorgestelde screening, vastgelegd voor nieuwe correlatieresultaten:
- Benaderingsdoel: per primaire afstand RMS <=0.01 en max-paarfout <=0.03.
- Gewenste numerieke reserve: chi32->64 per afstand RMS <=0.003 en
  max-paarverschil <=0.01. Ook bij slagen blijft dit een heuristische
  convergentiescreen, geen certificaat en geen hardware-goedkeuring.
- Bij slechte convergentie: eerst betere klassieke referentie, niet claimen
  dat het verschil met FLO de echte interactiefout is.
- Als ook correlaties goedkoop goed worden benaderd: geen voordeel claimen;
  onderzoeksvraag aanscherpen of langere tijden verkennen.

Eerste proef: CPU-only, een thread, maximaal 180 s voor de worker en 2 GiB
RSS. Geen installaties, geen QPU, geen chi128-run of T>0.4-run in deze stap.
Alle originele bestanden blijven intact; nieuwe uitkomsten in een eigen map.
Tijden voor het uitlezen van bewaarde MPS-toestanden zijn GEEN volledige
simulatietijden en mogen niet direct met QPU-gebruik worden vergeleken.

## Belangrijke valkuil bij de klassieke zes-tijdencontrole

Bereken eerst gemiddelde eerste EN tweede momenten en trek daarna het
product van gemiddelden af:
C_mix = mean_k(<m_i m_j>_k) - mean_k(<m_i>_k) mean_k(<m_j>_k).
Dit is niet hetzelfde als mean_k(C_ij,k). De spreiding van de lokale
profielen tussen trainingstijden veroorzaakt zelf klassieke correlaties.
Deze bijdrage behouden is noodzakelijk voor een eerlijke vergelijking.

## Vervolgfasen: nog niet uitvoeren of als voltooid presenteren

| Fase | Proef | Doorgangscriterium |
|---|---|---|
| A, nu | Bestaande T=0.4-correlaties + exacte 3x3-controle | Rekenmethode klopt; onderscheid en referentiezekerheid expliciet |
| B | Exacte 3x3-tijdcurves, U=0/4/8, T=0.4/0.8/1.2; eventueel richting 2 | Benaderingen toetsen op vooraf bevroren punten; dt-refinement |
| C | Geselecteerde 6x6-punten, MPS chi64/128/256 met tijd/RAM-caps | Convergentie en tijd-tot-gewenste-kwaliteit, inclusief goedkope alternatieven |
| D | Native circuitontwerp en kostenraming op Nighthawk | Uitvoerbare diepte, realistische onzekerheidsmarges en vers budget |
| E | Nieuwe hardwarepilot, alleen na nieuwe toestemming | Onafhankelijke validatie en gelijke kwaliteits-/tijdsgrenzen |

Bij langere T niet simpelweg twee steeds grotere Trotterstappen gebruiken.
Onderscheid circuitbenchmark (identiek eindig circuit) en fysische dynamica
(dt-convergentie naar het Hamiltoniaanprobleem). Neem bijvoorbeeld dt=0.2,
0.1,0.05 op kleine systemen als convergentiestudie; deze waarden garanderen
vooraf geen voldoende nauwkeurigheid. Meer tijdpunten kunnen klassiek uit
een traject worden verkregen: kosten niet naief met het aantal punten vermenigvuldigen.

## Klassieke tegenstanders en zwakste aannames

Eerst exact U=0 en de vaste mengcontrole, daarna geconvergeerde MPS waar
haalbaar; eventueel TDHF, cluster-/operator-methoden als aanvullende kandidaten.
Geen nieuwe methode als implementatie of benchmark presenteren voordat zij
daadwerkelijk is uitgevoerd. Het falen van een methode bewijst geen
klassieke onmogelijkheid. Zwakste aannames: chi64 als referentie, voldoende
hardware-signaal bij langere circuits en daadwerkelijke moeilijkheid van de
gekozen observabelen. Meer verstrengeling alleen is geen bewijs daarvoor.

Quantumkosten omvatten training, kalibratie, alle shots en nabewerking;
QPU-gebruik apart naast totale doorlooptijd. Klassieke kosten omvatten ook
de generatie van trainingsdata; geef koude worker en kernel apart.
Een 150,8/8-verhouding blijft geen matched-accuracy-claim.

## Bronnen en bestaande ankers

- [Wild & Alhambra, korte-tijddynamica](https://journals.aps.org/prxquantum/abstract/10.1103/PRXQuantum.4.020340): lokale observabelen hebben klassiek toegankelijke regimes; niet alle korte dynamica is een kans op advantage.
- [Artiaco et al., lokale informatie](https://journals.aps.org/prxquantum/abstract/10.1103/PRXQuantum.5.020352): complexe toestanden kunnen toch goed benaderbare lokale observabelen hebben.
- [Alam et al., 2D Hubbard op 72 qubits](https://arxiv.org/abs/2510.26845): motiveert interactiegevoelige fysica en onafhankelijke vergelijkingen; geen bewijs voor onze prestaties.
- Bewaar `hardware_tflo_dd6_2026-09-06_v1`, `classical_mean6_timing_2026-09-06_v1`
  en beide `classical_full_6x6_mps_T04*`-archieven als herkenbare ankers.

De physics-skill bepaalt conventies, onafhankelijke controle, stopcriteria
en het scheiden van diagnostische vooruitgang van een advantage-claim.
