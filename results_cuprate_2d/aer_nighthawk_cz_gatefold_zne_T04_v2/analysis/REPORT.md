# CZ-gatefolding ZNE in Aer

Gecorrigeerde seedopzet; 128 trajecten per factor, acht vaste twirls, U/t=8, T=0.4.
Primaire resultaten inclusief ongewijzigde analytische uitleesruis.

| Methode | Lading-RMSE | Spin-RMSE | Doublon-RMSE | Spincontrast g |
|---|---:|---:|---:|---:|
| raw128 | 0.07704 | 0.25000 | 0.09477 | 0.61668 |
| zne_linear_PRIMARY | 0.07114 | 0.16405 | 0.08248 | 0.75509 |
| zne_quadratic_SECONDARY | 0.08457 | 0.22598 | 0.07387 | 0.70976 |
| cz_noise_off_DIAGNOSTIC | 0.02431 | 0.08981 | 0.03745 | 0.86443 |

Primaire lineaire ZNE: spin-RMSE-afname 0.08594, 95%-interval [0.06122, 0.10315].
Relatieve afname 34.4%.
Positieve spinverbetering opgelost binnen dit model en deze steekproef.

## Opzet en grenzen

CZ-factoren 1,2,3 betekenen werkelijk 1008,2016,3024 uitgevoerde CZ-gates.
Extra CZ-paren behouden de ideale berekening. Op elke toegevoegde CZ werkt
hetzelfde volledige ruisproces: restdepolarisatie EN gate-time-relaxatie.
Lineaire interceptgewichten [4/3,1/3,-2/3] waren vooraf vastgelegd.
Kwadratisch [3,-3,1] is alleen een gevoeligheidscheck, niet achteraf gekozen.
De CZ-off-controle behoudt alle ideale CZ-gates en alle overige fouten.
Deze steekproefcontrole is geen fysiek beschikbare mitigation en geen exacte referentie.
Readout- en eenqubitfouten worden niet naar nul geextrapoleerd.
Geen clipping van onfysische extrapolaties; zie ranges_primary in results.json.
Foutmarges behouden de correlatie tussen ZNE en de hergebruikte raw-controle.
Het zijn alleen Monte-Carlo-intervallen voor conditionele verwachtingstrajecten,
niet voor fysieke bitshots; finale meetruisvariatie en modelbias ontbreken.
Geschatte spincontrast-standaardfout groeit met factor 1.56 versus raw128.
Krommingsdiagnostiek spincontrast: -0.02720; p=0.548 (asymptotisch).
ZNE-versus-CZ-off: 1 van 27 momenten buiten gezamenlijke Monte-Carlo-band.
Afwezigheid van gedetecteerde kromming/verschil bewijst geen juiste extrapolatie.
128 versus 64 zijn geneste subsets; geen volledige convergentieverklaring.

## Budget en verificatie

De ZNE-estimator gebruikt 384 trajecten (inclusief 128 hergebruikt), tegen raw128:
3x de trajecten en 6x de CZ-applicaties. Dit is geen gelijke-budgetvergelijking.
De afzonderlijke CZ-off-diagnose gebruikt nog 128 nieuwe trajecten.
Nieuwe simulatieruntijden: {"factor2_folded": 193.23241985999994, "factor3_folded": 220.13065980099782, "cz_noise_off_diagnostic": 227.8982632160005}.
Aer run+result-tijden zijn geen volledige end-to-end tijd of voorspelde QPU-facturatie.
De oude QPU-limiet van 5 seconden blijft onaangeraakt. Nieuwe QPU-seconden: 0.
27 tests geslaagd; onafhankelijke observabelefout 6.66e-16.
Alle nieuwe seeds gescheiden; noise-off-folds en modelidentiteit gecontroleerd.
Model mist idle-gap-ruis, coherente/contextuele fouten, crosstalk, leakage,
preparatiefouten en drift. Geen hardwareverbetering of quantum advantage bewezen.

Protocol: AER_CZ_ZNE_PROTOCOL.md; alle input, broncode en resultaten zijn gehasht.
