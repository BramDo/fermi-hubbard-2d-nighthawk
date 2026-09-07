# Voorstel volgende quantumkwaliteitsproef — NIET geautoriseerd

Doel: toetsen of de compacte circuituitvoering echt betere observabelen
geeft dan de oorspronkelijke TFLO-familie, bij hetzelfde fysieke probleem.
Geen klassieke moeilijkheidsscan; klassieke antwoorden zijn alleen controle.

Voorgestelde eenmalige vergelijking: oorspronkelijke parametrische familie
tegen nieuwe compacte familie, beide zonder DD. Zelfde layout,vier twirls,
512shots per instelling. Per arm zes U0-trainingstijden, twee aparte U0-
holdouts en een U8-doel bijT0.4:72dynamische circuitinstellingen plus vier
all0/all1-readoutkalibraties =76x512=38,912shots. Volgorde vooraf bevroren en
armen interleaven; kalibratievolgorde op providerniveau niet gegarandeerd.

Readoutcorrectie en vaste affine TFLO afzonderlijk per arm, zonder tijdfeature
of training op U8/MPS-antwoorden. Zowel raw/readout als TFLO publiceren.
Geen ZNE,PEC,postselectie of extra DD in deze specifieke vergelijking.

Primair: gepaarde foutvergelijking op de twee U0-holdouts met exacte eindige-
circuitreferenties. Verbeterde ruwe/readout-data en gevalideerde TFLO apart
beoordelen. De bestaande holdoutscreen blijft een screen, geen certificaat.
Secundair: lading,spin,doublons bijU8 tegenover bestaande chi64, inclusief
onzekerheidsmarges en dezelfde controle zonder doelhardware-input. Chi64 is
geen exact antwoord. Negatieve kansen niet clippen of verbergen.

Voorgestelde harde cap voor EEN nieuwe job:15QPU-seconden, alleen na nieuwe
toestemming EN geslaagde verse budgetcontrole. Dit document geeft die
toestemming niet. Geen automatische herhaling of hergebruik van oude locks.

Nog nodig voor gereedmelding: verse backendstatus/faults/timing/layout/ISA;
planning van shots,rep-delay,reset en provider-overhead; geverifieerde bound-
invoer en metadata; nieuwe exclusieve pogingmarker; provider-capcontrole;
volledige archivering van ruwe data, werkelijk uitgevoerde circuits en verbruik.
De offline80-us-schatting is geen toezegging over jobkosten of voltooiing.

Ook bij een korter circuit kan de pilot falen:20,736CZ blijft een grote
belasting. Bij falende holdouts geen betrouwbare6x6-reconstructie claimen.
