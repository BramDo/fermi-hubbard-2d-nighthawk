# 6x6 TFLO/DD-pilot afgerond: budget gehaald, validatie niet gehaald

De hardwarejob is voltooid en alle meetgegevens zijn gecontroleerd. TFLO
verkleint de afstand tot onze klassieke chi=64-uitkomst sterk, maar levert
hier geen gevalideerd herstel van de observabelen. Beide onafhankelijke
holdoutcontroles falen en de doelmetingen voegen geen aantoonbare waarde
toe boven de vooraf vastgelegde controle zonder doelhardware-input.
Geen quantum advantage aangetoond. Geen nieuwe hardwarejob gestart.

## Uitvoering en budget

- Job `daesvo51ierc738mji3g`, backend `ibm_phoenix` (Nighthawk).
- Providerstatus DONE; 8 QPU-seconden afgerekend, ingestelde cap 15 seconden.
- Alle 76 uitgevoerde circuits komen overeen met de opgeslagen invoer.
- Alle 38.912 shots zijn aanwezig: 512 per circuit. Per DD-arm en fysische
  instelling zijn vier twirls samengenomen: 2.048 shots. Het totale aantal
  shots betreft dus niet uitsluitend het U=8-doel.
- 6 september 2026: RUNNING 20:41:06.510 UTC, afgerond 20:45:26.882 UTC.
  Deze ongeveer 260 seconden wandkloktijd zijn niet hetzelfde als QPU-gebruik.
- Provider `circuits_execution_time_ns`: 4.734678016 seconden. Dit is niet
  de totale doorlooptijd van compilatie, training, ophalen en mitigatie.
- Eenmalige autorisatie verbruikt; de oorspronkelijke pogingmarker blijft
  bestaan. Geen automatische herhaling, nieuwe job of verhoogd budget.

Het volledige model bleef behouden: 6x6 sites, 72 fermionmodi, 32 deeltjes
(16 up + 16 down), t=1, t'=-0.25, U=8, T=0.4 en twee symmetrische stappen.
Spin betekent n_up-n_down, niet S_z. De vergelijking betreft het eindige
Trottercircuit, geen gecertificeerde continue tijdsevolutie.

## Resultaten voor U=8, T=0.4

RMS is de afstand over de 36 sites tot de opgeslagen, niet-gecertificeerde
MPS-berekening met chi=64. Dit zijn geen exact vastgestelde hardwarefouten.

| Methode | N | RMS lading | RMS spin | RMS doublons |
|---|---:|---:|---:|---:|
| Oude 6x6: readout + CZ-ZNE | 35.768 | 0.279 | 0.703 | 0.165 |
| Nieuwe pilot: readout, DD uit | 35.574 | 0.275 | 0.703 | 0.160 |
| Nieuwe pilot: readout, DD aan | 35.593 | 0.281 | 0.703 | 0.163 |
| Readout + TFLO, DD uit; niet gevalideerd | 32.562 | 0.093 | 0.080 | 0.058 |
| Readout + TFLO, DD aan; niet gevalideerd | 32.078 | 0.072 | 0.091 | 0.052 |
| Controle zonder U=8-hardware-input, DD-aan-fit | 32.001* | 0.029 | 0.058 | 0.011 |

*Afgerond; geen selectie of geforceerde N=32 toegepast. Zie de volledige
profielen en onzekerheidsintervallen in `analysis/summary.json`.

De oude run had een andere native compilatie, andere shots/twirls en een
ander uitvoermoment. Deze historische vergelijking is dus geen zuivere
causale meting van het effect van TFLO of DD. De nieuwe native basis bevat
20.736 CZ-gates, tegenover 15.400 in de oude factor-1-run. De compilerwijziging
behoudt de logische fysica maar maakt deze run niet shallow.

## Waarom de kleinere RMS-afstanden geen validatie zijn

1. **De aparte U=0-holdouts falen.** Vooraf vereiste de screening bij beide
   tijden een bovenkant van het conditionele 95%-RMS-interval van maximaal
   0.05 voor lading/spin en 0.03 voor doublons. Beide DD-armen falen.
   Bij T=0.4 zijn de TFLO-spin-RMS-afstanden 0.395 (DD uit) en 0.378
   (DD aan), tegenover de exact berekenbare U=0-circuitreferentie.
   De bovenkanten van hun intervallen zijn 0.422 en 0.412, ver boven 0.05.
   Ook T=0.2 faalt. Status: `DIAGNOSTIC_UNVALIDATED`.

2. **De correctie geeft onfysische lokale kansen.** Bij het U=8-doel is de
   kleinste afgeleide onsite-kans -0.0881 zonder DD en -0.1052 met DD.
   Negatieve schattingen zijn niet geclipt of verborgen; ze zijn geen
   fysische gereconstrueerde toestand. N=32.078 alleen bewijst geen herstel:
   het conditionele 95%-interval is bovendien [30.917, 33.132].

3. **De doelhardware-input verbetert de controle niet.** De vooraf gekozen
   ablatietest vervangt deze input door het gemiddelde van de zes
   trainingsinputs. Dezelfde geleerde TFLO-fit geeft dan kleinere afstanden
   voor alle drie observabelen. Voor DD aan is de TFLO-winst ten opzichte
   van deze controle negatief; de conditionele 95%-intervallen zijn
   [-0.106,-0.042] voor lading, [-0.087,-0.024] voor spin en
   [-0.074,-0.036] voor doublons. De controle gebruikt nog trainingshardware,
   maar geen U=8-doelshots. Dit toont geen nuttige doelhardware-informatie aan.

4. **Een aanvullende, achteraf gemaakte klassieke diagnose bevestigt dit.**
   Het rekenkundige gemiddelde van uitsluitend de zes exacte U=0-
   trainingsprofielen geeft RMS [0.029306, 0.057594, 0.011377], zonder enige
   hardware-input. Dit is een expliciet post-hoc diagnosticum, geen nieuw
   gevalideerd algoritme of vervanging van de vooraf vastgelegde screening.
   De nabijheid van TFLO aan chi=64 kan hier grotendeels uit de training
   voortkomen; zij bewijst niet dat het U=8-signaal uit de ruis is gehaald.

## Wat doet DD op zichzelf?

In de gematchte readoutarmen zijn alle punt-RMS-afstanden met DD iets groter.
Voor de RMS-winst van DD (uit minus aan) zijn de conditionele 95%-intervallen:
lading [-0.01349,+0.00013], spin [-0.00796,+0.00682], doublons
[-0.00670,+0.00200]. Alle drie omvatten nul. Geen aantoonbare DD-winst.
Dit geldt voor deze circuits, timing en vier vaste twirls; geen algemene
uitspraak dat DD nooit helpt.

DD is daadwerkelijk uitgevoerd als expliciete native X-X-echo's. Dat de
ingebouwde Runtime-DD-optie uit stond, betekent niet dat deze arm geen DD had.
DD-aan en -uit behouden dezelfde oorspronkelijke gate-starttijden en duur.

## Methode en grenzen

Readoutcorrectie gebruikt gepoolde all-0/all-1-kalibraties en onafhankelijke
asymmetrische uitleeskanalen. In beide armen zijn handmatige CZ-Pauli- en
readout-X-twirls gebruikt. De affine TFLO-fit per Z/ZZ-observable gebruikt
alleen zes U=0-trainingstijden (0.04,0.08,0.12,0.24,0.32,0.48), ridge 0.001
naar de identiteitscorrectie en geen tijdfeature. Holdouts (0.20,0.40),
U=8-doeldata en chi=64-antwoorden zijn niet gebruikt om de fit te trainen
of te selecteren. Geen ZNE, PEC, sectorpostselectie, MESR of GPR in deze job.
Dit is een beperkte TFLO-variant, niet de volledige mitigatiestack uit de
[Google/Phasecraft-paper](https://arxiv.org/html/2510.26845v2).

De 400 bootstrapreplica's omvatten hele shots, gedeelde onafhankelijke
kalibratieonzekerheid en opnieuw fitten. De intervallen zijn conditioneel
op vier vaste twirls, niet simultaan en niet coverage-gecertificeerd.
Drift, gecorreleerde SPAM, transferbias van TFLO, Trotterfout en MPS-truncatie
zitten er niet in. Ook chi=64 is niet geconvergeerd gecertificeerd: het
verschil chi32->64 is RMS [0.014735,0.055382,0.020637].

De conclusie is niet 'alleen meer shots nodig'. Shots verminderen de
statistische spreiding, maar deze pilot toont tevens een falende geleerde
correctie en geen nuttige bijdrage van de doelmetingen. Eerst betrouwbare
controlepunten en een gevalideerde minder diepe circuitroute; niet op basis
van deze pilot meer hardwarebudget claimen.

## Verificatie en bewaring

Alle oorspronkelijke data en bevroren invoer zijn ongewijzigd bewaard.
Aanvullende onafhankelijke controles:

- Directe integer-decoding reproduceert alle ruwe doelprofielen exact.
- Directe paar-kansinversie versus Pauli-readoutcorrectie: maximaal 2.22e-16.
- Onafhankelijke affine least-squaresfit: maximaal 4.22e-14 verschil.
- RMS-afstanden en de controle zonder doelinput onafhankelijk exact herhaald.

Zie `provider_metrics.json`, `retrieval_verification.json`,
`raw_bitstrings.json`, `provider_result_complete.json`, `provider_inputs/`,
`analysis/summary.json`, `analysis/verification.json`, `analysis/bootstrap_dd*.npz`
en `delivery_audit.json`. Analysebroncode en het protocol blijven bevroren.
`audit_delivery_tflo_dd6.py` legt alleen de aanvullende eindcontrole vast.
`delivery_sha256.json` controleert het volledige opleverarchief;
`git_qpy_mirrors/manifest.json` documenteert verliesloze gecomprimeerde QPY-
kopieen voor Git. De ongecomprimeerde originelen blijven op schijf.

De skills get-physics-done en fire-opal-safe-api bepaalden de onafhankelijke
controles, scheiding tussen diagnose en validatie, budgetbewaking en behoud
van ruwe data. Alles blijft lokaal; geen publicatie of push uitgevoerd.
