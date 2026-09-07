# Eerste CZ-half-screen: behouden, maar statistische claim ingetrokken

De bestanden in analysis/ zijn het oorspronkelijke, ongewijzigde resultaat.
Spin-RMSE 0.20802 -> 0.16801 gaf een puntschatting van 19.2% verbetering.
Het oorspronkelijke interval mag NIET als geldig bewijs worden gebruikt.

Na de analyse is ontdekt dat opeenvolgende twirlseeds overlappen met de
per-shot seeds van Aer 0.17.2. De onafhankelijke bootstrap onderschat hier
de onzekerheid van het spincontrast (diagnostische factor circa 2.1 voor
de controle). Dit maakt de puntschatting niet automatisch onjuist, maar
haar aanvankelijke zekerheid is niet gerechtvaardigd.

De oude 512-bitshotcontrole had spincontrast 0.58959, tegenover 0.68522
hier. Dat verschil mag niet alleen aan meetruis worden toegeschreven:
spincontrast is lineair. Gedeelde seeds dragen bij aan onderschatte
foutmarges, maar verklaren niet bewezen de volledige afwijking.

De nieuwe primaire vergelijking is het naastgelegen archief
aer_nighthawk_full_cz_half_T04_v2_disjoint_seeds, met vooraf vastgelegde,
gescheiden seedbereiken. Geen gegevens zijn vervangen of weggegooid.
De circuit-, model- en noise-off-controles van v1 blijven bewaard.
Deze v1-status is COMPLETE_BUT_INDEPENDENT_BOOTSTRAP_INVALID.
Nieuwe QPU-seconden: 0.
