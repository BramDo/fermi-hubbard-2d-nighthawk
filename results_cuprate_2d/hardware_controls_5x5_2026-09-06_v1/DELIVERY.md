# Controle afgerond: voorbereiding redelijk goed, diepe dynamica faalt

Job daer9j5nj4cs73afhofg, ibm_phoenix/Nighthawk, DONE.
12 circuits,6144 shots; providergebruik **3 QPU-seconden**, cap5 bevestigd.
De preflightraming was4.172s bij2 interne deeljobs. Geen tweede indiening.

## Gemeten uitkomst

Onderstaande getallen zijn na de vooraf vastgelegde readoutcorrectie.

| Controle | Exact N | Gemeten N | Conditioneel95%-interval N | RMS spinfout |
|---|---:|---:|---|---:|
| 5x5 alleen voorbereiding | 22 | 21.8969 | [21.8448,21.9527] | 0.00588 |
| 6x6 alleen voorbereiding | 32 | 31.8720 | [31.8030,31.9350] | 0.00602 |
| 5x5 U=0,T=0.4 | 22 | 24.8612 | [24.6982,25.0215] | 0.33991 |

De voorbereidingen zijn niet foutloos: hun resterende N-bias is groter dan
de hier berekende statistische onzekerheid. Hun lokale afwijkingen zijn wel
klein: charge-RMS0.0064/0.0070 en doublon-RMS0.0038/0.0031 voor5x5/6x6.
De U0-dynamica faalt veel sterker: charge-RMS0.23891,spin-RMS0.33991,
doublon-RMS0.09572 tegenover een exact berekenbare eindige-circuitreferentie.
Ruwe N-waarden zijn21.9355,31.8818 en24.8452: readoutcorrectie herstelt de
dynamica niet. Alle ruwe en gecorrigeerde resultaten zijn bewaard.

## Onafhankelijke controles

- De5x5-begintoestand heeft3 gaten,22 deeltjes (11up/11down); de6x6-controle
  gebruikt de oorspronkelijke4 gaten en32 deeltjes (16up/16down).
- De dynamische controle gebruikt50 modi,t=1,t-prime=-0.25,U=0,T=0.4,
  twee symmetrische tijdstappen en7600 CZ. Vier twirls x512 shots.
- De gecompileerde U0-poortstructuur is gelijk aan de lokaal bewaarde
  U8-companion. De U8-companion is NIET ingediend.
- De FLO-referentie is exact voor het ideale eindige U0-circuit. Het verschil
  met continue evolutie is apart berekend: RMS charge0.00487,spin0.00253,
  doublon0.00222; halveren van de stap geeft ongeveerviermaal kleinere fout.
- Alle12 werkelijk uitgevoerde provider-QPYs behouden het bedoelde ideale
  deeltjesaantal bij onafhankelijke achterwaartse operatorpropagatie.
  De grootste residu-plus-pruningmaat is1.70e-12; dit is numeriek gecontroleerd,
  geen intervalrekenkundig bewijs. Zes onafhankelijke dense tests geven
  maximaal4.44e-16 afwijking.
- Alle6144 shots,12 provider-inputs en metadata zijn gecontroleerd.
  Onafhankelijke uitleesmatrixinversie en Pauli-analyse verschillen maximaal
  3.33e-16. Acht nieuwe tests en29 bestaande regressietests slagen.

## Begrenzing van de conclusie

De grote afwijking verschijnt bij de diepe uitvoering, ook zonder fysieke
U-interactie. Dat wijst op uitvoerings-/ruiseffecten, niet op de keuze32 of
een fout in de onderzochte tel-, masker- of ideale deeltjesbehoudketen.
Het bepaalt niet welke afzonderlijke gate-, reset-, coherentie- of
uitleescontextfout de oorzaak is. Een klein voorbereidingsbias blijft bestaan.

De95%-intervallen zijn conditioneel: whole-shot bootstrap bij vaste varianten
en gedeelde onafhankelijke kalibratietrekkingen. Drift, gecorreleerde SPAM en
readout-modelbias ontbreken. De72-bitkalibratie wordt voor5x5 beperkt tot de
eerste50 fysieke kanalen; contextonafhankelijkheid is een modelaanname.
Kalibraties waren nominale bookends; interne uitvoeringsvolgorde is niet
gegarandeerd. Geen clipping,postselectie,TFLO-fit,ZNE,PEC ofqDRIFT gebruikt.

Vervolgadvies: eerst werkelijk minder CZ-lagen met een nieuwe U0-controle;
alleen T verlagen met hetzelfde poortskelet verkort de hardware-uitvoering
niet vanzelf. Nog niet opschalen naar nieuwe U8- of6x6-dynamica.
Deze uitslag zegt niet dat elk5x5-algoritme of Nighthawk in het algemeen faalt.
Een volgende hardwarejob vereist nieuwe toestemming.

## Archief

- analysis/RAPPORT.md en analysis/summary.json: volledige vaste analyse.
- references.json: exacte circuitreferenties en Trotterconvergentie.
- native_number_verification.json: onafhankelijke volledige circuitcontrole.
- raw_bitstrings.json,provider_result_complete.json,provider_inputs/:
  originele data en werkelijk uitgevoerde circuits.
- source_snapshot/,additional_checks/,LOG_at_delivery.md: broncode,
  extra verificatie en log. De eerste lokale compile-onderbreking is bewaard;
  hervatten met meer processtack veranderde geen poorten of fysica.
- delivery_sha256.json: integriteit van het eindarchief, uitgezonderd de
  append-only werklog LOG.md. De canonieke indieningsvergrendeling blijft
  buiten deze map staan en is als snapshot meegeleverd.

Physics- en veilige-API-skills stuurden onafhankelijke controles, vaste
claimgrenzen, de5-secondenlimiet en precieseen indiening.
