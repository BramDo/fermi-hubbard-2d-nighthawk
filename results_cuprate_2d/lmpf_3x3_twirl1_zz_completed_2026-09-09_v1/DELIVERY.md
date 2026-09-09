# Twirl1 ZZ afgerond: exacte-normcontroles geslaagd, ruwe Gram-grens niet

De ontbrekende chi256-arm met CZ-factor3 is afgerond. Er is precies EEN nieuwe
operatorstaat berekend; de zeven eerder voltooide staten zijn byte voor byte
overgenomen. De aanvullende procedure duurde158.02s en bleef binnen de
goedgekeurde300s. De oorspronkelijke tijdslimietmelding blijft bewaard.

De volledige onafhankelijke audit slaagt. Alle drie centrale operatoren van
twirl1 hebben nu passende coefficienten met geslaagde vooraf vastgelegde
exacte-norm/G/b-stabiliteitscontroles. Dit is nog GEEN hardware-validatie.

## Volledige ZZ-vergelijking chi128 naar chi256

| Controle | Verandering | Grens | Status |
|---|---:|---:|---|
| Ruwe volledige Gram-matrix | 1.312959% | 1% | NIET geslaagd |
| Volledige Gram-matrix met exact F00=1 | 0.179909% | 1% | geslaagd |
| Noisy/noisy blok G | 0.135111% | 1% | geslaagd |
| Ideaal/noisy overlapvector b | 0.504992% | 1% | geslaagd |
| L1-verandering shot-aware coefficienten | 0.01801090 | 0.05 | geslaagd |

De ruwe ideale norm stijgt van0.9799880399 naar0.9938862683; exact is deze1.
De normcorrectie was vooraf vastgelegd en verandert ALLEEN F00 in een aparte
matrixkopie. Ruwe waarden blijven bestaan. G, b en de coefficienten veranderen
er niet door: F00 is een constante in de optimalisatie.

De positieve conclusie geldt dus voor de EXACTE-NORM-controles, niet voor de
ruwe volledige Gram-matrix. Ook met de exact bekende norm is dit geen bewijs
van asymptotische convergentie of een foutgrens voor echte hardware.

| Niveau | factor1 | factor2 | factor3 |
|---|---:|---:|---:|
| chi128 | 1.9221543994 | -0.1918382974 | -0.7303161020 |
| chi256 | 1.9311598484 | -0.1946802135 | -0.7364796349 |

Som(c)=1. Shot-aware eta1,N=(43,7,14), dezelfde readout-kalibratie en beide
centrale modi. Geen targetdata of referentiewaarden gebruikt voor de fit.
De negatieve coefficienten zijn niet afgeknipt.

Chi256 surrogate projectiefout0.3591759324, voorwaardelijke
samplingvariantiegrens0.1392612653, objective0.4984371977.
Deze getallen zijn geen gecertificeerde hardware-MSE- of observablefoutgrenzen.

## Drie centrale operatoren van twirl1

| Operator | Niveaus | Exacte-norm F-verandering | L1 coefficientverandering |
|---|---|---:|---:|
| Z_up | chi64/128 | 0.085839% | 0.00718143 |
| Z_down | chi64/128 | 0.078576% | 0.00834277 |
| Z_up Z_down | chi128/256 | 0.179909% | 0.01801090 |

Alle bijbehorende G/b-controles slagen ook. Dit betreft slechts het centrale
paar van een3x3-rooster en twirl1. Geen volledige27-observable/eight-twirl-
validatie, nieuwe hardwarewaarden of automatisch6x6-go.

## Tijd, verificatie en bewaring

- Archiefjob daem7r642tqs73autong, backend ibm_phoenix,18 actieve modi.
- 3x3 Hubbard,U8,T0.4,twee symmetrische circuitstappen.
- Gezamenlijk ZZ op modes8/9, fysiek109/108.
- Alleen native providerrecord2,factor3,3024 CZ, werd opnieuw gepropageerd.
- Nieuw gegenereerde staat:133.949s; volledige hervatprocedure:158.022s.
- Dit is EXTRA rekentijd naast de eerdere circa590s-budgetstop, niet de
  totale ZZ-voorbereidingstijd. Importopstart is apart.
- Onafhankelijke audit:11.713s; archiefintegriteit4/4 objecten geslaagd.
- 75 tests,20 onafhankelijke overlaps,twee directe KKT-fits.
- Maximale overlapafwijking2.22e-15; coefficientafwijking4.44e-15.
- Zeven oude staten en hun metadata byte voor byte gecontroleerd.
- Vier grote chi256-staten verliesloos opgeslagen in acht delen onder10MB;
  alle lokale originelen zijn behouden. Geen bestanden verwijderd.
- Geen QPU-tijd, target-scoring, publicatie of push.

De physics-verificatieskill bepaalt dat de ruwe mislukte grens zichtbaar blijft
naast de geslaagde exacte-normcontrole. De oude foutmelding staat ongewijzigd
in parent_failure.json en in de oorspronkelijke resultaatmap.

## Volgende stap

De [hardware-heranalyse](NEXT_HARDWARE.md) kan nu worden uitgevoerd op de
OPGESLAGEN twirl1-metingen, met passende eigen gewichten voor alle drie
operatoren. Dat is nodig om te zien of lading, spin en doublons werkelijk
verbeteren. Het is nog niet uitgevoerd.

Herstel de grote bestanden na een clone, indien nodig:

```bash
python -B lmpf_2d/portable_archive.py restore results_cuprate_2d/lmpf_3x3_twirl1_zz_completed_2026-09-09_v1
```

De restorer weigert bestaande afwijkende bestanden te overschrijven.
