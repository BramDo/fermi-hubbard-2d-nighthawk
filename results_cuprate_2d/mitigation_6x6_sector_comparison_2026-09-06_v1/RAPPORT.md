# 6x6: extra sector-mitigatie op bestaande hardwaredata

Geen nieuwe hardwarejob: 0 extra QPU-seconden. Bronjob daen2vdnj4cs73afcn00.
Dit is een verkennende heranalyse, niet de nog ontbrekende TFLO/DD-hardwaretest.

| Methode | N | RMS lading versus chi64 | RMS spin versus chi64 | RMS doublon versus chi64 |
|---|---:|---:|---:|---:|
| raw_factor1 | 35.76929 | 0.27854 | 0.70384 | 0.16459 |
| readout_factor1 | 35.75664 | 0.27814 | 0.70416 | 0.16442 |
| readout_cz_zne | 35.76763 | 0.27860 | 0.70341 | 0.16471 |
| strict_sector_factor1_no_readout_inverse | 32.00000 | 0.26544 | 0.71511 | 0.13056 |
| cz_zne_then_sector_ratio_no_readout_inverse | 32.00000 | 0.28807 | 0.72580 | 0.14277 |

## Uitkomst en grenzen

Strikte selectie behoudt per CZ-factor 1/2/3 respectievelijk [48, 46, 45] van 4096 shots.
N=32 en totale spin=0 zijn door dit filter afgedwongen en bewijzen geen herstelde dynamica.
De sectorarmen bevatten GEEN readout-inversie. De oude readout+ZNE-arm blijft apart staan.
De ratio-arm extrapoleert de ongenormaliseerde teller en noemer met vaste gewichten (4/3,1/3,-2/3).
ZNE+sector noemer95%: [0.007080078125, 0.017008463541666664]; status: EXPLORATORY_RATIO_FINITE_DENOMINATOR_NOT_VALIDATED.

Gepaarde vermindering in RMS-afstand raw minus strikte selectie (lading, spin, doublon): [0.013097832607660453, -0.011276425469619822, 0.03403377602310706].
Bijbehorende 95%-intervallen: [[-0.033043580575966056, -0.04730335106208163, 0.004106752890670492], [0.021176890981275693, 0.011001094845244948, 0.03941102875245894]].
Een kleinere afstand tot chi64 is geen foutcertificaat: chi64 is nog niet geconvergeerd.

Exploratory conditional whole-shot PUB bootstrap; old readout arms also use shared independent-channel calibration draws. Excludes drift, correlated readout, selection and extrapolation bias, MPS and Trotter error. Not equal shot budgets.

## Nog nodig voor de gevraagde sterkere mitigatie

TFLO vereist passende 6x6-U=0-trainingsmetingen plus onafhankelijke holdouts. De 3x3-fit en 5x5-controle kunnen dit niet vervangen.
DD is een pulsaanpassing tijdens uitvoering en kan niet achteraf aan opgeslagen shots worden toegevoegd.
Nieuwe metingen uitsluitend na een verse raming en expliciete budgettoestemming; oude toestemming is verbruikt.
Zie het bewaarde protocol voor een matched DD-aan/uit en TFLO-vervolgontwerp.
De physics-skill leidde tot afzonderlijke armen, een onafhankelijke decodercheck en expliciete selectie-/referentiebiasgrenzen.

Bron: [Google/Phasecraft, Methods: Error mitigation](https://arxiv.org/html/2510.26845v2).
