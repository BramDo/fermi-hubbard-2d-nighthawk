# 6×6: hardware en klassieke controle

Alle 13.312 metingen zijn opgehaald. De 26 werkelijk uitgevoerde circuits zijn byte-identiek aan de vastgelegde circuits. IBM rapporteert **5 QPU-seconden**, binnen de ingestelde limiet van 15 seconden. Er is geen nieuwe hardwarejob gestart.

## Hardware: deze mitigatie is nog niet voldoende

Het ideale circuit moet exact **32 deeltjes** behouden. Dat lukt niet in de gemeten data:

| Methode | Shots, inclusief kalibratie | Deeltjesaantal N | 95%-bootstrapinterval |
|---|---:|---:|---|
| Ruw | 4.096 | 35,769 | 35,645–35,900 |
| Readout | 5.120 | 35,757 | 35,627–35,893 |
| Readout + CZ-ZNE | 13.312 | 35,768 | 35,561–35,976 |

Er is dus geen vergelijking bij gelijk shotbudget. De vaste ZNE-fit herstelt het bekende deeltjesbehoud niet.

De ruwe shot-standaardfout van N is ongeveer **0,067**, tegenover een afwijking van **3,769**. Louter te weinig onafhankelijke shots verklaart dit niet. Meer shots kunnen de statistische spreiding verkleinen, maar verwijderen niet vanzelf een systematische verschuiving. De precieze foutbron is hiermee nog niet vastgesteld.

De intervallen omvatten shotvariatie bij vaste twirls en onzekerheid in de aangenomen onafhankelijke uitleeskanalen. Ze omvatten geen drift, gecorreleerde SPAM of extrapolatiebias en zijn geen gecertificeerde totale foutgrenzen.

## Parallel uitgevoerd: χ=64

De volledige klassieke 6×6-berekening met één BLAS-thread is klaar:

- Rekentijd: **150,819 seconden**; inclusief imports: **156,905 seconden**.
- Deeltjesaantal: **31,999999197**.
- Tijd gemeten tijdens ander lokaal werk, niet als geïsoleerde prestatiebenchmark.

| Verschil χ=64 tegenover χ=32 | Lading | Spin | Dubbele bezetting |
|---|---:|---:|---:|
| RMS | 0,014735 | 0,055382 | 0,020637 |
| Grootste verschil per site | 0,034024 | 0,076968 | 0,037949 |

De vooraf gekozen stabiliteitsgrens van 0,01 RMS wordt nog overschreden. **χ=64 is geen gecertificeerde referentie. χ=128 is niet gestart.**

Vergeleken met χ=64 verandert het spin-RMS-verschil door readout + ZNE slechts van 0,703838 naar 0,703409. De geschatte verbetering van 0,000429 heeft een hybride 95%-interval van −0,002790 tot 0,003460: geen overtuigend positief mitigatie-effect. Dit zijn verschillen tegenover een benadering, geen gemeten fouten tegenover een exact antwoord.

## Hoe lang zou χ=128 duren?

Gemeten: χ=32 kostte 32,183 seconden; χ=64 kostte 150,819 seconden. Dat is een factor 4,686.

| Extrapolatie | Raming χ=128 |
|---|---:|
| Nogmaals dezelfde gemeten factor | 11,8 minuten |
| Ruw kubisch schaalmodel: 8× | 20,1 minuten |

**Voorlopige planningsraming: 12–25 minuten.** Dit is geen meting, statistisch interval of gegarandeerde bovengrens; het kan langer duren. 15 × 150 seconden is inderdaad 37,5 minuten, maar factor 15 volgt niet uit de huidige metingen.

De generieke kubische kosten van veel MPS-SVD-stappen staan in tabel 1 van [Paeckel et al.](https://arxiv.org/abs/1901.05824). De minutenraming hierboven is onze eigen extrapolatie voor deze pc, niet een resultaat uit dat artikel.

## Wat is aangetoond?

Alle **41 gezamenlijke tests** zijn geslaagd. Een onafhankelijke uitleesmatrixinversie en lineaire fit reproduceren de hardware-observabelen tot 6,7 × 10⁻¹⁶. De opgeslagen klassieke MPS is apart met NumPy gecontracteerd; de afwijking in de momenten is kleiner dan 4,2 × 10⁻¹⁵.

De physics- en veilige-API-controles hebben de vaste analyse, onafhankelijke verificatie en het behoud van de oorspronkelijke gegevens bewaakt.

**Geen voordeel bij gelijke nauwkeurigheid of end-to-end snelheidsvoordeel aangetoond.** De 5 QPU-seconden zijn niet de totale doorlooptijd: IBM aanmaak-tot-afronding was 138,776 seconden; de eenmalige lokale circuitvoorbereiding kostte 657,224 seconden. Archivering en analyse komen daar nog bij.

Alle ruwe bitstrings, providerresultaten, circuits, kalibratie, bootstrapdata, klassieke toestanden, broncodekopieën en controlesommen zijn bewaard.

