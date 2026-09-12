# Symbolische 3x3-formules: dezelfde getallen teruggevonden

De parameters zijn vast: 3x3 open, N_up=N_down=4, middengat, t=1, t_prime=-1/4, U=8. T blijft een symbolische variabele in eenheden hbar/t. Er is niet op de eerder berekende getallen gefit.

## Een expliciete formule

De gemiddelde dubbelbezetting begint als:

$$
\overline D(T) = - \frac{17512379 T^{8}}{90720} + \frac{76631 T^{6}}{1080} - \frac{877 T^{4}}{54} + \frac{16 T^{2}}{9} + O(T^{10}).
$$

Dit zijn alleen de eerste termen. Voor de getallen hieronder is de volledige polynoom tot en met T^108 gebruikt, met exact rationale coëfficiënten. De oneindige reeks is exact; de eindige polynoom heeft een gecontroleerde afkapfout. De korte formule hierboven mag dus niet zonder meer bij T=0.4 worden afgekapt.

## Resultaten

| T | D/site uit formule | Spinprofiel-RMS uit formule | Evaluatie, mediaan (s) |
|---|---:|---:|---:|
| 0.1 | 0.016222765199 | 0.902815544199 | 0.003741 |
| 0.2 | 0.049209299932 | 0.811290350214 | 0.005160 |
| 0.4 | 0.064354264250 | 0.685165729385 | 0.004805 |

Grootste verschil over alle 27 lokale observabelen en de drie tijdstippen met de eerdere numerieke referentie: 7.661e-15.
De rationeel berekende uniforme afkapgrens voor iedere lokale ladingswaarde op |T|<=0.4 is 5.058e-13; voor lokale spin en doublon is de grens de helft. Dit is een grens op de reeksafkap, niet op de oude numerieke referentie.

Door symmetrie zijn de vier hoeken gelijk en de vier randmiddens gelijk. Het centrum is de derde groep. Alle negen sites worden daarmee beschreven, zonder de volledige sector te verkleinen.

Exacte identiteiten op elke berekende orde: N(T)=8, totale spin=0 en norm=1. Spin_RMS is sqrt((4*S_corner^2+4*S_edge^2+S_centre^2)/9).

## Wat voor symbolische oplossing is dit?

De coëfficiënten volgen uit machten van de gehele matrix A=4(H-16I). De scalaire verschuiving verandert alleen een globale fase. Geen numerieke eigenwaarden, matrixexponentiële tijdsolver of fitting is gebruikt om de polynomen te bouwen of in te vullen. SymPy controleert de exact oplosbare tweetoestandstest sin(T)^2.

Dit is een expliciete symbolische machtreeks voor het interagerende model, geen korte eindige combinatie van sinussen en cosinussen. Een volledige gesloten elementaire oplossing van het 15.876-dimensionale probleem is hiermee niet gevonden.

## Tijd en opslag

Exacte gehele matrixmachten: 8.490 s. Coëfficiënten afleiden: 5.976 s. Hele worker: 20.941 s. De kleine evaluatietijden in de tabel sluiten deze eenmalige afleiding uit.

- coefficients.json: alle exacte breukcoëfficiënten.
- full_formulas.txt / full_formulas.tex: de volledige expliciete polynomen.
- evaluations.json: alle lokale waarden.
- convergence.json: wat er verandert bij afkappen op lagere orde.
- verification.json / VERIFICATION.md: algebraïsche en numerieke controles.
- theory/SYMBOLIC_3X3_DERIVATION.md: afleiding, eenheden en foutgrens.

Geen QPU gebruikt. Dit resultaat geldt voor deze 3x3-instantie, niet automatisch voor 6x6.
