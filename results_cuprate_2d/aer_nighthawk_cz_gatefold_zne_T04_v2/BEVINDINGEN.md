# Uitkomst: echte CZ-gatefolding ZNE in Aer

Primaire spin-RMSE: 0.25000 zonder ZNE -> 0.16405 met lineaire ZNE.
Relatieve verandering: 34.4% minder fout.
95%-interval relatieve verbetering: [23.1%, 43.2%].
Absolute spin-RMSE-afname: 0.08594, interval [0.06122, 0.10315].
Verbetering zichtbaar binnen de conditionele Monte-Carlo-onzekerheid van dit model.

| Grootheid | Raw128 | Lineaire ZNE (primair) |
|---|---:|---:|
| Lading-RMSE | 0.07704 | 0.07114 |
| Spin-RMSE | 0.25000 | 0.16405 |
| Doublon-RMSE | 0.09477 | 0.08248 |
| Spincontrast g | 0.61668 | 0.75509 |

## Interpretatie

Dezelfde 3x3, 18-qubit, U/t=8, T=0.4, twee-Trotterstappen en acht twirls.
Factoren 1,2,3 hebben 1008,2016,3024 echte CZ-applicaties per circuit.
Elk extra CZ-paar is ideaal de identiteit, maar behoudt de volledige gekalibreerde
gatefout. Dit is daadwerkelijke digitale gatefolding in de simulator.
Het schaalt CZ-gateaantallen; het is niet gegarandeerd een uniforme vermenigvuldiging
van het effectieve ruiskanaal. T1/T2-ruis hoeft niet met de CZ te commuteren.
De extrapolator en plaatsingsseeds waren vooraf vastgelegd; geen selectie op succes.
Alleen CZ-ruis wordt versterkt. Eenqubit- en uitleesfouten blijven bestaan.
De afzonderlijke CZ-noise-off-controle geeft spin-RMSE 0.08981 en g=0.86443.
Deze controle is zelf een Monte-Carlo-schatting, geen exact of hardwarebereikbaar resultaat.
Lineaire ZNE wijkt bij 1 van 27 momenten af
van CZ-off buiten de gezamenlijke 95%-Monte-Carlo-band; dit toetst resterende extrapolatiebias.
Kwadratische ZNE geeft spin-RMSE 0.22598; uitsluitend een secundaire gevoeligheidscheck.
Methodeafhankelijkheid en ontbrekende modelruis vallen niet binnen de vermelde intervallen.
Onfysische negatieve twee-modekansen bij de primaire puntschatting: 0.
Er is niets geclipt. ZNE-momenten hoeven geen positieve dichtheidsmatrix te vormen.
Standaardfout spincontrast wordt circa 1.56x die van raw128.
Dit zijn conditionele ruistrajecten met analytische readout, geen echte 512-shotmeting;
de extra uiteindelijke bitstring-meetvariantie is hier niet gesimuleerd.

## Budget en validatie

384 nieuwe productietrajecten: 128 bij factor2, 128 bij factor3, 128 diagnostisch.
Factor1 hergebruikt de 128 gecontroleerde trajecten met gescheiden seeds.
ZNE gebruikt 3x zoveel trajecten en 6x zoveel CZ-applicaties als raw128.
Dus geen conclusie over winst bij gelijk tijd-/shotbudget of binnen de oude 5s-QPU-limiet.
Nieuwe ZNE-run+result-simulatietijd: 413.36 s; diagnostiek: 227.90 s.
Totaal nieuw: 641.26 s (10.69 min), exclusief opzet en audits.
Nieuwe QPU-seconden: 0; geen submit-lock of hardwarejob aangepast.
27 regressietests; alle 24 noise-off circuits gecontroleerd.
Maximale noise-off-afwijking 2.26e-14;
onafhankelijke observabelefout 6.66e-16.
Bootstrap-foutpropagatie en bewaarde gatevolgordes nogmaals onafhankelijk gereproduceerd.
Alle code en resultaten bewaard, inclusief mislukte preflight-v1 en diens oorspronkelijke broncode.
De QPY save-expval-compatibiliteit is hersteld via reconstructie uit de oorspronkelijke meetcircuits.
Een kunstmatige Kraus-depolarisatietest met geforceerde fusion faalde numeriek;
die bevinding blijft gedocumenteerd. Exacte depolarisatie- en Kraus-relaxatietests slagen.
Geen modelparameter aangepast wegens die testfout.

Dit is nog geen aangetoonde Nighthawk-hardwaremitigatie of quantum advantage.
Volledige tabellen, kromming, geneste steekproefchecks en onzekerheden: analysis/results.json.
Protocol: AER_CZ_ZNE_PROTOCOL.md.
