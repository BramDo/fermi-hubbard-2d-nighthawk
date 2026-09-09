# Twirl1 ZZ: zeven staten bewaard, gestopt op tijdslimiet

De ZZ-berekening is NIET volledig afgerond. De vooraf vastgelegde
blokgrenscontrole stopte de rekenprocedure na ongeveer590s, binnen de harde
600s-proceslimiet. Er is geen automatische herstart uitgevoerd.

| Niveau | Opgeslagen staten | Status |
|---|---|---|
| chi128 | ideaal, noisy factor1/2/3 | compleet |
| chi256 | ideaal, noisy factor1/2 | bewaard |
| chi256 noisy factor3 | geen voltooide staat | ontbreekt |

Er ontbreken dus geen zeven berekeningen: alleen de LAATSTE arm moet nog
worden afgemaakt. Die arm moet opnieuw vanaf zijn eigen begin worden berekend;
de overige zeven volledige staten blijven herbruikbaar met hashcontrole.
De afgebroken tussenstand van de laatste arm is niet als complete staat opgeslagen.

## Wat wel is gecontroleerd

- 72 tests geslaagd voordat de berekening begon.
- Correcte gezamenlijke ZZ-operator op mode8/9, fysiek109/108.
- Readout-penalty uit beide kalibratiemodi en alle vier uitkomsten.
- Kleine exact controle: een noisy ZZ-operator is niet in het algemeen het
  product van twee afzonderlijk geëvolueerde noisy Z-operatoren.
- De zeven opgeslagen staten, maskers, native QPY- en bronhashes zijn geverifieerd.
- 16 beschikbare overlaps onafhankelijk herberekend:10 bij chi128,6 tussen
  de drie beschikbare chi256-staten. De volledige chi128-fit is nagecontroleerd.
- Maximale chi128-Gram-afwijking7.77e-16; coefficientafwijking4.44e-15.
- Drie grote chi256-bestanden verliesloos gearchiveerd in zes delen onder10MB.
  Alle drie reconstructiehashes kloppen. Originelen blijven lokaal aanwezig.

De gedeeltelijke audit duurde6.30s; het archiveren en de integriteitscontrole
7.86s. Dit waren afzonderlijke, vooraf voorziene controles na de rekenstop.
Geen extra operatorpropagatie, target-scoring of QPU-tijd.

## Wat nog niet geconcludeerd kan worden

De volledige chi256-Gram-matrix en chi256-coefficienten ontbreken. Er is GEEN
complete chi128/256-stabiliteitsvergelijking. De ontbrekende arm is niet door
nul, een twirl0-staat of een afgeleide van losse Z-operatoren vervangen.

De chi128-gewichten zijn[1.9221543994,-0.1918382974,-0.7303161020].
Ze zijn alleen een tussenresultaat en nog niet op hardwaredata toegepast.
De ruwe ideale chi128-norm is0.9799880399; de aparte exact-normmatrix behoudt
F00=1 zonder G, b of de gewichten te veranderen.

Z_up en Z_down van twirl1 hadden hun eigen lokale controles eerder gehaald.
ZZ blijft ONVOLTOOID. Er zijn geen nieuwe lading-, spin- of doublonresultaten,
geen gevalideerde hardwareverbetering en geen groen licht voor6x6.

## Provenance en vervolg

Archiefjob daem7r642tqs73autong op ibm_phoenix, twirl1,18 actieve modi,
3x3 Hubbard,U8,T0.4,twee symmetrische circuitstappen.
Native providerrecords25/19/2, CZ-factoren1/2/3.
De ongewijzigde canonical-MPS-kernel en bevroren depolariserende surrogate
zijn gebruikt; overlapguard3e9 FLOPs/2^22 elementen is expliciet ingesteld.

[Voorbereide hervatting](NEXT_MISSING_ARM.md): uitsluitend chi256/factor3,
met maximaal300s extra lokale rekentijd na akkoord, daarna de volledige
matrix- en stabiliteitscontrole. Niet opnieuw alle acht staten berekenen.

De physics-verificatieskill houdt de gedeeltelijk geverifieerde bestanden
gescheiden van een voltooide stabiliteitscontrole. De foutmelding en het
budgetstop-record zijn bewaard. Niets is verwijderd of gepubliceerd.

Na een clone kunnen de grote staten veilig worden hersteld met:

```bash
python -B lmpf_2d/portable_archive.py restore results_cuprate_2d/lmpf_3x3_twirl1_zz_2026-09-09_v1
```

De restorer weigert een bestaand afwijkend bestand te overschrijven.
