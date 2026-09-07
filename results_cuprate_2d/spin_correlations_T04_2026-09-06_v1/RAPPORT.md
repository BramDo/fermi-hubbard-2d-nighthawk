# Eerste proef onderzoeksvoorstel: spincorrelaties maken het onderscheid zichtbaar

Het onderzoeksvoorstel is uitgewerkt en de eerste lokale ankerproef is
afgerond. De vaste U=0-mengschatting die de lokale profielen goed benaderde,
benadert de verbonden spincorrelaties duidelijk minder goed. Dit is reden
om de meetvraag verder te onderzoeken, geen bewijs van quantum advantage.
Ook de 6x6-MPS-referentie is hiervoor nog niet voldoende geconvergeerd.

Er is geen nieuwe hardwarejob gestart: 0 extra QPU-seconden. De rekenworker
was na 18,87 s klaar, binnen de limiet van 180 s. Dat is heranalyse van
bewaarde MPS-toestanden plus een nieuwe exacte 3x3-controle, geen volledige
nieuwe 6x6-evolutie en geen end-to-end-snelheidsbenchmark.

## Meetvraag

C_ij=<m_i m_j>-<m_i><m_j>, met m_i=n_up-n_down=2S_z. De getallen hieronder
zijn voor C_m, dus viermaal C_Sz. Alle verschillende siteparen zijn bewaard;
de vooraf gekozen hoofdanalyse splitst ze naar Manhattan-afstand 1, 2 en 3.
Het gaat om de volledige bestaande t-t'-U-circuitfysica bij T=0.4, twee
stappen dt=0.2. Nog geen dt-convergentie naar continue Hamiltoniaandynamica.

## 6x6: RMS-afstanden van verbonden spincorrelaties

| Vergelijking | Afstand 1, 60 paren | Afstand 2, 98 paren | Afstand 3, 116 paren |
|---|---:|---:|---:|
| Vast U=0-trainingsmengsel tegenover chi64 | 0,064685 | 0,068562 | 0,076576 |
| U=0 op dezelfde T=0.4 tegenover chi64 | 0,025074 | 0,040293 | 0,008522 |
| MPS chi64 tegenover chi32 | 0,015221 | 0,004744 | 0,002659 |

Voor alle 630 ongeordende paren samen is de RMS voor het U=0-mengsel
0,077504 en de maximale paarafwijking 0,122836. Het getekende gemiddelde
van die afwijkingen is slechts -0,001677: positieve en negatieve verschillen
vallen daar grotendeels weg. Daarom mag dat kleine gemiddelde niet worden
gebruikt als bewijs van goede overeenkomst.

De voorgestelde benaderingsscreen (per primaire afstand RMS<=0.01 en
max-paarafwijking<=0.03) wordt door beide U=0-varianten niet overal gehaald.
Bij U=0 op T=0.4 gaat afstand 3 wel goed, maar afstanden 1 en 2 niet.

De vooraf gewenste MPS-reserve (RMS chi32->64<=0.003 en max<=0.01 per afstand)
faalt vooral bij afstand 1. Daar is de maximale chi-verandering 0,033516.
**Chi64 is daarom nog geen voldoende gecontroleerde referentie om de
6x6-afwijkingen exacte fysische fouten te noemen.** Zelfs een geslaagde
verschiltest zou op zichzelf geen gecertificeerde foutgrens opleveren.

## Exacte 3x3-controle

Voor 3x3 is een nieuwe volledige 18-qubit-statevector berekend van hetzelfde
eindige circuit, onafhankelijk van de opgeslagen MPS-toestanden.

| Methode tegenover exact 3x3 | RMS alle 36 paren | Maximale paarfout |
|---|---:|---:|
| MPS chi16 | 0,017232 | 0,044587 |
| MPS chi32 | 0,006401 | 0,013727 |
| MPS chi64 | 0,001252 | 0,001951 |
| Vast U=0-trainingsmengsel | 0,049469 | 0,076800 |
| U=0 op T=0.4 | 0,015960 | 0,029529 |

De grotere chi verbetert de correlaties aantoonbaar op dit kleine exacte
anker. De vrije mengschatting faalt hier dus ook zonder onzekerheid over
de exacte circuitreferentie. Dat geeft inhoudelijk steun aan de nieuwe
meetvraag. Het bewijst niet dat 6x6 bij chi64 even nauwkeurig is, en 3x3
blijft zelf klassiek goed berekenbaar.

## Waarom de mengschatting nu tekortschiet

Het gemiddelde van lokale profielen kan bij een eindpunt goed lijken,
terwijl het niet de juiste samenhang tussen sites bevat. Bovendien genereert
het mengen van verschillende U=0-tijden zelf klassieke correlaties:

C_mix = mean(C_k) + Cov_k(m_k).

Die tweede term is correct meegenomen en onafhankelijk gecontroleerd. Het
maximum van deze tussen-tijd-covariantie is bij 6x6 ongeveer 0,1205. We hebben
de klassieke controle dus niet kunstmatig verzwakt door deze term weg te
laten. Verbonden correlaties kunnen ook klassiek zijn; een niet-nul C is
geen verstrengelingsgetuige en geen advantage-bewijs.

## Onafhankelijke verificatie

- Zes unit-tests geslaagd: willekeurige MPS versus dense contractie,
  producttoestand, mengcovariantie, FLO-Wick versus volledige 2x2-evolutie,
  afstandsgroepering en veiligheidslimieten.
- Alle oorspronkelijke lokale MPS-profielen gereproduceerd, maximaal
  3,89e-15 verschil. Normen binnen 2,5e-14 van een.
- 3x3-correlaties opnieuw uit directe sitekansen: maximaal 2,17e-15 verschil.
- Vijf vaste 6x6-paren onafhankelijk als vier-mode-operator met Quimb:
  maximaal 1,34e-15 verschil met de NumPy-transfermethode.
- Covariantie-identiteit voor het trainingsmengsel: 3,34e-16.
- Alle 28 bevroren bron-/invoerhashes en 24 analysehashes gecontroleerd.

De gebruikte duurmetingen komen van een monotone klok. UTC-logtijd is alleen
voor herkenning; tijdens deze run is een kleine klokcorrectie zichtbaar.
Er is geen statistische shotruis in deze klassieke proef. Wel bestaan
MPS-truncatie, roundoff en voor continue dynamica nog Trotterfout.

## Vervolg en stopgrens

De volgende inhoudelijke fase uit het voorstel is een kleine 3x3-tijdscan
met U=0/4/8 en tijdstapverfijning. Daarmee kiezen we vooraf te valideren
punten waar de goedkope schattingen tekortschieten. Voor kwantitatieve
6x6-claims is daarnaast een begrensde chi128-convergentiecontrole nodig.
Geen chi128/256, T>0.4-evolutie of nieuwe hardware is nu uitgevoerd.

Pas na referentieconvergentie volgt een nieuwe circuit- en budgetcontrole.
Dat de U=0-schatting faalt is onvoldoende: betere klassieke methoden kunnen
de correlaties nog steeds snel voorspellen. De quantumcomputer moet ook
dezelfde vooraf gekozen kwaliteit halen, met alle kosten meegeteld.

Zie het voorstel `ONDERZOEKSVOORSTEL_SPINCORRELATIES_2D.md` in de projectroot,
plus `summary.json`, alle momentmatrices, `exact_3x3_state.npz`,
`independent_verification.json`, tests, log en broncodekopieen in deze map.
Oude hardware-, timing- en MPS-archieven zijn ongewijzigd. De physics-skill
bewaakte de conventies, onafhankelijke ankers, stopcriteria en claimgrenzen.
