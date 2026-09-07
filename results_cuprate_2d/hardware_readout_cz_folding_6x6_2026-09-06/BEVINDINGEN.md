# 6x6-resultaten: opgehaald en onafhankelijk gecontroleerd

Job daen2vdnj4cs73afcn00 op ibm_phoenix: alle13312 metingen en26 uitgevoerde circuits gecontroleerd.
IBM rapporteert5 QPU-seconden, binnen de ingestelde limiet15. Geen nieuwe job of herhaling.

## Hoofdbevinding

Geen quantum-advantagedemonstratie: het ideale circuit bewaart exact32 deeltjes, maar de ruwe en gemitigeerde data geven beide circa35,77.
Readout + CZ-ZNE herstelt dit behoud niet. De lokale spinprofielen zijn vrijwel vlak; dit zegt niet dat de volledige quantumtoestand is gereconstrueerd.

| Methode | Shots inclusief kalibratie | N | 95%-bootstrapinterval N |
|---|---:|---:|---|
| Ruw, factor1 | 4096 | 35.769287 | [35.644519, 35.900146] |
| Readout, factor1 | 5120 | 35.756642 | [35.627481, 35.892905] |
| Readout + CZ-ZNE | 13312 | 35.767629 | [35.561147, 35.975543] |
| ZNE zonder readout (diagnostisch) | 12288 | 35.780192 | [35.584847, 35.981529] |

Geen gelijk shotbudget:4096 ruw tegenover13312 voor readout+ZNE.
Intervallen:2000 whole-shot replicaties bij vaste twirls plus gedeelde onafhankelijke Jeffreys-uitleeskalibratietrekkingen.
Niet gelijktijdig of dekkingsgecertificeerd; drift, gecorreleerde SPAM, extrapolatiebias, Trotterfout en MPS-truncatie ontbreken.

## Alleen te weinig shots?

De ruwe shot-standaardfout van N is0.06748; de afwijking van32 is3.76929.
De normale shot-only95%-benadering is[35.63702, 35.90156].
Louter eindige onafhankelijke shotstatistiek verklaart deze afwijking niet.
Meer shots verkleinen de statistische spreiding als1/sqrt(shots), maar verwijderen op zichzelf geen systematische verschuiving. De foutbron is hiermee niet volledig geïdentificeerd.

## Parallelle klassieke controle

Chi64: 150.819s rekenkern; 156.905s cold worker; één BLAS-thread.
Gemeten tijdens ander lokaal werk, niet als geïsoleerde prestatiebenchmark.

| Verschil chi64 minus chi32 (één thread) | Lading | Spin | Dubbele bezetting |
|---|---:|---:|---:|
| RMS | 0.014735 | 0.055382 | 0.020637 |
| Maximaal per site | 0.034024 | 0.076968 | 0.037949 |

Vooraf vastgelegde stabiliteitsscreen geslaagd: False.
Chi64 is niet als gecertificeerde referentie gebruikt. De opgeslagen72-mode-MPS is onafhankelijk met NumPy gecontracteerd; momentverschil kleiner dan4,2e-15.

## Hardware versus de benaderende chi64-referentie

| Methode | RMS verschil lading | RMS verschil spin | RMS verschil dubbele bezetting |
|---|---:|---:|---:|
| Ruw, factor1 | 0.278536 | 0.703838 | 0.164594 |
| Readout, factor1 | 0.278142 | 0.704158 | 0.164419 |
| Readout + CZ-ZNE | 0.278595 | 0.703409 | 0.164708 |
| ZNE zonder readout (diagnostisch) | 0.278972 | 0.703116 | 0.164909 |

Dit zijn verschillen tegenover een benadering, geen fouten tegenover een exact antwoord.
Spinverschilreductie door readout+ZNE: 0.000429; hybride95%-interval [-0.002790, 0.003460].
Geen overtuigend positief mitigatie-effect aangetoond. Alle chi-referenties zijn opgenomen in VERIFICATION.json.

## Raming chi128

Gemeten chi32: 32.183s; chi64: 150.819s; verhouding 4.686.
Nogmaals dezelfde verhouding: 11.8minuten. Kubisch model (8x): 20.1minuten.
Voorlopig12-25minuten plannen, geen gemeten tijd of gegarandeerde bovengrens. Meer tijd is mogelijk.
15x150s is37,5minuten, maar factor15 volgt niet uit deze metingen. Chi128 is niet gestart.
Generieke kubische MPS-SVD-kosten: tabel1 van [Paeckel et al.](https://arxiv.org/abs/1901.05824). De minutenraming is onze eigen extrapolatie, niet een resultaat uit dat artikel.

## Tijd en bewijs

QPU-gebruik:5s; IBM aanmaak-tot-afronding: 138.776s.
Eenmalige lokale circuitvoorbereiding: 657.224s; archivering/analyse komen daar nog bij.
Geen end-to-end of matched-accuracy-snelheidsvoordeel vastgesteld.
Alle41 gezamenlijke tests geslaagd; onafhankelijke native-readoutmatrixinversie plus aparte lineaire fit wijkt maximaal 6.66e-16 af.
Physics- en veilige-API-skills stuurden de onafhankelijke controles, vaste fit, claimgrenzen en het behoud van eerdere gegevens.
Ruwe bitstrings, providerresultaat, werkelijk uitgevoerde QPY-circuits, kalibratie, bootstrapdata, broncodekopieën en controlesommen zijn bewaard.
