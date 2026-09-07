# TFLO 3x3: compacte hardwarepilot voltooid

## Nieuwste lokale audit: 0 extra QPU-seconden

Zie `tflo_transfer_circuit_audit_2026-09-05/BEVINDINGEN.md` en het volledige
`summary/AUDIT_REPORT.md`. De eerdere resultaten en locks zijn ongewijzigd.

- TFLO-overdracht: de huidige fit geeft U=8-MSE 0.033645; een geheel
  klassieke U=0-tijdcurve geeft 0.031355. Zonder tijdterm wordt TFLO slechter
  (0.074497). De winst van echte U=8-input tegenover dezelfde fit met U=0-
  input is niet statistisch duidelijk. Dit is een verkennende diagnose,
  geen bewijs dat alle hardware-informatie afwezig is of TFLO algemeen faalt.
- Routing: de huidige netwerkroute blijft de beste van vijf exact
  equivalente kandidaten (1008 CZ, twee-qubitdiepte 144). Geen nieuwe
  gatebesparing gevonden; geen nieuwe hardwaretest uitgevoerd.
- Exacte-H/Trottercontrole: spin-RMSE op T=0.4 daalt bij 2/4/8 stappen van
  0.038274 naar 0.008356 en 0.002020. De huidige meet-/mitigatiefout tegenover
  het tweestapscircuit is groter (0.2051). Rechtstreeks tegenover exacte H
  is de huidige hardware-TFLO-spin-RMSE 0.2422.
- Verificatie: 20 tests, 32 numerieke controles en 14 extra auditchecks
  geslaagd; 400/400 bootstrapreplicaties bruikbaar. Alle nieuwe gegevens,
  circuittests, broncode en Hamiltonianreferenties zijn afzonderlijk bewaard.

Vervolgvoorstel: eerst lokaal gevarieerdere U=0-calibratie bij dezelfde
dynamische diepte ontwerpen en het interactiecontrast toetsen. Nog geen
nieuwe QPU-job, geen nieuwe primaire methode en geen quantum advantage.

## Laatste resultaat: DONE, 4 QPU-seconden gebruikt

De apart goedgekeurde compacte job `dae5gat1ierc738lmg10` op ibm_phoenix
is voltooid. De provider bevestigt de 5-secondenlimiet; werkelijk verbruik
is 4 QPU-seconden. Alle 80 circuits en 5120 shots zijn ontvangen en de
providerinputs komen overeen met de bevroren intentie. Geen herhaling.

Zie `tflo_compact_run_3x3_2026-09-05/primary_analysis/RESULT_REPORT.md`.

- Vooraf vast filter met tolerantie 1: 141/512 behouden shots op U=8,T=0.2
  en 190/512 op U=8,T=0.4. Fit alleen op zes nieuwe U=0-trainingspunten;
  de twee U=0-validatiepunten en U=8 bleven buiten de fit.
- Spin-RMSE raw -> TFLO: 0.5319 -> 0.0869 bij T=0.2 en
  0.4226 -> 0.2051 bij T=0.4. Gepoolde Pauli-MSE: 0.264518 -> 0.033645.
- De goedkope klassieke U=0-FLO-voorspelling heeft MSE 0.033533.
  Het 95%-interval voor klassiek-minus-TFLO winst is [-0.005389, 0.004674].
  Dus wel duidelijke verbetering tegenover raw, maar niet tegenover die
  klassieke controle; geen quantum advantage.
- 400/400 bootstrapreplicaties bruikbaar, geen filterwijziging of clipping.
  Onafhankelijke centrale observabelen komen exact overeen. Eindcontrole:
  35 controles, 207 artifacthashes en 26 regressietests geslaagd.
- Fysische grenscontrole: bij T=0.2 is de doublonschatting op site 4
  (nulgebaseerd) -0.01948, dus buiten [0,1]. Het 95%-bootstrapinterval
  [-0.03749, 0.03710] bevat nul. Dit is ongewijzigd gerapporteerd, niet geclipt;
  er wordt geen volledig fysische of foutvrije reconstructie geclaimd.
- Beschrijvend tegenover de vorige job: ruwe MSE 16.8% lager, maar TFLO-MSE
  0.030717 -> 0.033645, dus geen betere eindnauwkeurigheid. Door mogelijke
  hardwaredrift is dit geen causaal A/B-bewijs voor de circuitopschoning.

Alle ruwe bits, oorspronkelijke en providerinputs, volledige resultaten,
broncode, vaste analyse, bootstrapreplicaties en beide indieningslocks
zijn bewaard. De nieuwe toestemming is door deze ene poging verbruikt.

## Voorbereiding van de compacte hardwarepilot

Zie `tflo_compact_review_2026-09-05/NEXT_STEP_REPORT.md` voor het eerdere
voorbereidingsverslag. Die voorbereiding gebruikte 0 QPU-seconden en
veronderstelde nog geen nieuwe toestemming. De later apart gegeven
toestemming leidde tot de ene job hierboven; de oude lock is niet hergebruikt.

- Zelfde 3x3-model, mapping op ibm_phoenix, tijdstippen en shots:
  10 instellingen x 8 twirls x 64 shots = 5120 totaal, 512 per instelling.
  Alleen de al gevalideerde een-qubit-opschoning verandert de circuits.
- De nieuwe analyse staat vooraf vast: tolerantie 1 uit de vorige verkenning,
  minimum 32, ridge 0.001, nieuwe fit uitsluitend op zes U=0-trainingspunten.
  U=0-validatie en U=8 blijven buiten de fit. De klassieke U=0-voorspelling
  is een verplichte comparator, niet alleen raw. Geen filterwijziging achteraf.
- 448 lokale controles, alle 80 bound-QPY-roundtrips, 916 actuele read-only
  preflightchecks, 25 afsluitende controles en 13 unit-tests geslaagd.
- Shotuitvoering plus reset/rep_delay: 0.114237 s. Inclusief overhead is de
  raming 2.114 s bij een interne subjob, 4.114 s bij twee en 6.114 s bij drie.
  Het aantal subjobs is onbekend: dit is geen bovengrens of prijsopgave.
  Voorstel na toestemming: max_execution_time=5, geen sessie/batch/retry.

De nieuwe templates zijn nog niet op hardware getest. De oorspronkelijke
strikte analyse, ruwe hardwaredata en indieningsblokkering blijven intact.
Een historische vergelijking bewijst door mogelijke hardwaredrift geen
causaal effect van de opschoning, en deze kleine pilot bewijst geen quantum advantage.

## Voorafgaande lokale heranalyse: 0 extra QPU-seconden

Zie `tflo_followup_2026-09-05/FOLLOWUP_REPORT.md` voor beide afzonderlijke
vervolgsporen. De oorspronkelijke hardwaredata en gestopte primaire analyse
zijn niet gewijzigd; er is geen extra job gestart.

- Eén-qubit-gates samengevoegd vóór parameterbinding: X/SX-aantal 42.4%
  lager, diepte 887-906 naar 623-637, nog steeds 1008 CZ per circuit.
  138 controles en exacte QPY-herlaadgelijkheid geslaagd; maximale
  statevectorafwijking 2.944e-14. Deze nieuwe circuits zijn niet op hardware getest.
- Een verkennend filter is gekozen uitsluitend met U=0-trainings- en
  validatiedata: abs(N_up-4)+abs(N_down-4)<=1, minimum 32 behouden shots.
  Dit behoudt 176 en 157 shots op de twee U=8-punten. De oorspronkelijke
  strikte analyse blijft als mislukt bewaard.
- Op de bestaande U=8-data wordt de spin-RMSE 0.5829 -> 0.0745 bij t=0.2
  en 0.4792 -> 0.2047 bij t=0.4. Gemiddelde kwadratische Pauli-fout:
  0.318025 -> 0.030717. Onzekerheid gecontroleerd met 400 bootstrapreplicaties,
  inclusief filterherselectie op U=0. De precieze filterkeuze is niet stabiel.
- Belangrijke controle: uitsluitend de klassieke U=0-FLO-voorspelling geeft
  MSE 0.033533 op deze U=8-doelen, bijna hetzelfde als TFLO. Het interval
  voor de extra winst boven die voorspelling bevat nul. Geen statistisch
  duidelijk voordeel boven die klassieke controle en geen quantum advantage.

U=8-antwoorden werden niet voor selectie of fitting gebruikt, maar de ruwe
U=8-resultaten waren eerder bekeken: dit is verkennend, niet een nieuwe
blinde bevestiging. 59 archief-/reproductiechecks en 7 unit-tests geslaagd.

## Uitkomst van de eenmalig goedgekeurde hardwarejob

Job `dae3rou42tqs73au78d0` op ibm_phoenix is DONE. De provider bevestigt
de limiet van 5 QPU-seconden; werkelijk verbruik is 4 seconden. Alle 80
circuits en alle 5120 shots zijn ontvangen. De daadwerkelijk opgeslagen
providerinputs en resultaatmetadata komen overeen met de bevroren intentie.

Strikte selectie op N_up=N_down=4 houdt 374 van de 5120 shots over:
27-50 per instelling. Drie instellingen halen de vooraf vastgelegde
minimumdrempel van 32 niet. Daarom is de primaire TFLO-fit niet uitgevoerd.
Het filter is niet achteraf aangepast en er is geen job herhaald.

Zie `tflo_run_3x3_2026-09-05/RESULT_REPORT.md` voor de uitkomst en
`sector_diagnosis.json` voor alle aantallen en diagnostische ruwe meetfouten.
Alle ruwe bitstrings, inputs, volledige providerresultaten, metrics en
indieningsblokkering blijven bewaard. De primaire analyse toonde geen
mitigatiewinst. De latere verkennende heranalyse hierboven laat wel
foutreductie zien ten opzichte van raw, maar geen quantum advantage.

De actuele, herlaadbare voorbereiding staat in `tflo_pilot_3x3_2026-09-05_ready/`.
Het onafhankelijke opslag- en testverslag staat in
`tflo_pilot_3x3_2026-09-05_ready_audit/VERIFICATION.md`.

## Voorafgaande budgetcontrole (voor de hardwarejob)

Zie `tflo_budget_2026-09-05/BUDGET_REPORT.md` en de bijbehorende JSON-raming.
Op de actuele ibm_phoenix zijn alle 80 bevroren circuits ISA-compatibel;
928 controles zijn geslaagd. De 5120 shots vragen volgens de lokale
gate-/meet-/reset-/rep-delayberekening samen 0.14569984 seconde.
Met de door IBM beschreven circa 2 seconden opstartoverhead per intern
jobdeel wordt dit circa 2.146 seconden bij een deel of 4.146 seconden
bij twee delen. Drie delen komen op circa 6.146 seconden, boven de cap.

Het aantal interne jobdelen en de werkelijke overhead zijn niet vooraf
gegarandeerd. De bestaande harde 5-secondenlimiet blijft ongewijzigd.
Deze voorafgaande controle diende geen job in en gebruikte geen QPU-tijd.
De daaropvolgende, afzonderlijk geautoriseerde job staat hierboven;
er geldt nog steeds geen automatische retry.
De usage-API gaf verbruik terug, maar geen resterende allocatie; daaruit
is geen resterend tegoed afgeleid.

## Geverifieerd

- Volledig t-t-prime-U model; 3x3, 18 modes, N_up=N_down=4, twee vaste stappen.
- Exact dezelfde native gate-structuur voor U=0 kalibratie en U=8 validatie.
- 98/98 controles van fysica, expliciete twirls, meetmap en exacte QPY round-trip.
- 682/682 archiefchecks en 12/12 lokale unit-tests geslaagd.
- Grootste FLO versus volledige statevector afwijking: 1.7841284005726266e-13.
- Native template: 1008 CZ, diepte 549; de vorige numeriek geoptimaliseerde
  ZNE-pilot had 928 CZ. De TFLO-template is dus niet goedkoper per circuit.
- Opslag van ruwe Sampler-bitstrings per twirl, deeltjesaantalfiltering,
  regularized linear-linear TFLO en een hierarchische bootstrap zijn gebouwd.
- Een synthetische archief-naar-analyse-smoketest verwerkte 10 instellingen,
  80 twirls en 5120 shots; afwijkende metadata werd geweigerd. Dit waren
  uitsluitend tijdelijke softwaretestdata, geen nieuwe QPU-metingen.

## Vooraf vastgelegd meetplan en budgetgrens

6 U=0 trainingstijden, 2 afzonderlijke U=0 validatietijden en 2 U=8
validatiepunten. Per instelling 8 twirls x 64 shots = 512 shots, dus
5120 shots inclusief kalibratie. Vooraf was voltooiing binnen de bestaande
cap van 5 QPU-seconden niet gegarandeerd. De eenmalige run is vervolgens
met die ongewijzigde cap uitgevoerd; geen hoger budget verondersteld.

Backend- en kostencontrole, expliciete begrensde submissietoestemming en
archivering van daadwerkelijke providerinputs/bitstrings zijn uitgevoerd.
De prepare- en budgetscripts blijven submit-vrij. De aparte eenmalige
runner is nu vergrendeld tegen herhaling.

## Wetenschappelijke grenzen

De referenties betreffen de eindige productformule, niet exact exp(-iHT).
De fit ziet alleen de U=0 trainingsantwoorden. U=8 referenties zijn voor
validatie, nooit voor fitting. De vaste ridge-prior is een prototype en niet
de geleerde drietrapsregularisatie uit het paper. Onzekerheidsintervallen
bevatten geen U-afhankelijke transferbias. Er is geen aangetoonde verbetering
op hardware en geen quantum-advantageclaim.

Symmetrie-averaging is bewust nog uitgeschakeld: niet-triviale ruimtelijke
symmetrieen van H en de beginstaat zijn op dit eindige-Trotter-referentierooster
niet exact. MESR, GPR en dynamische decoupling zijn niet in deze stap toegevoegd.

## Bewaarde tussenversies en opgeloste problemen

- `tflo_pilot_3x3_2026-09-05/`: eerste referentie-/compileerproef, 1296 CZ.
  Niet als uitvoerbaar circuitarchief gebruiken: native QPY was niet herlaadbaar.
- `tflo_pilot_3x3_2026-09-05_fixed_constants/`: 1008 CZ na expliciet numeriek
  maken van constante fSWAP-hoeken. Native QPY nog niet herlaadbaar.
- `tflo_pilot_3x3_2026-09-05_ready/`: actuele versie; dezelfde gates, maar de
  globale fase analytisch geherformuleerd als korte affiene expressie.
  Geen fase of gates verwijderd; exacte QPY-herlaadgelijkheid getest.

De gecompileerde globale fase had een expressietekst van 75268 tekens.
QPY v13-v16 faalde met een uint16-groottelimiet; v17 schreef data die de
reader niet kon parsen. Een minimale parametercircuittest werkte wel;
de globale fase isoleren lokaliseerde de fout. Nu faalt voorbereiding
onmiddellijk als een QPY-bestand niet exact kan worden teruggelezen.
Alle oorspronkelijke tussenversies blijven bewaard; niets is overschreven.

Bronnen: [2D-paper, Appendix E](https://arxiv.org/abs/2510.26845v2),
[IBM QPY-formaat](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qpy),
[IBM Sampler-bitstrings](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.primitives.BitArray).
