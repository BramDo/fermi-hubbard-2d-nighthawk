# 512-shotvergelijking: het basismodel is te optimistisch

De lokale Aer-proef is afgerond: **512 nieuwe synthetische shots**, met
dezelfde acht twirls, elk 64 shots, als de bestaande hardwarepilot.
Meetpunt: 3x3 Hubbard, 18 actieve qubits, U/t=8, T=0.4, twee Trotterstappen.
Dit is een vergelijking op een meetpunt, niet de volledige tienpuntsreeks.

**Uitkomst:** dit kalibratiegebaseerde basismodel bootst de gemeten hardware
nog niet voldoende na om er betrouwbare absolute voorspellingen voor
hardware-mitigation op te baseren. Aer wijkt minder af van de ideale
circuitreferentie dan de echte hardware. Er zijn geen ruisparameters gefit.

| Methode | Data | Behouden | RMSE lading | RMSE spin | RMSE doublon |
|---|---|---:|---:|---:|---:|
| Ruw | Aer | 512/512 | 0.0876 | 0.2676 | 0.0997 |
| Ruw | Hardware | 512/512 | 0.1290 | 0.4226 | 0.1319 |
| Deeltjesfilter, tolerantie 1 | Aer | 224/512 | 0.0843 | 0.2205 | 0.0818 |
| Deeltjesfilter, tolerantie 1 | Hardware | 190/512 | 0.1305 | 0.4022 | 0.1128 |

Alle RMSE's zijn over negen sites ten opzichte van dezelfde exacte ideale
FINITE circuitreferentie. Spin is n_up-n_down, niet de halve hiervan.
TFLO, PEC en ZNE zijn niet toegepast in deze vergelijking.

## Meer dan alleen shotruis in de vergelijking

Voor het vaste acht-twirlensemble liggen **9 van de 27 ruwe Pauli-verschillen**
buiten een gelijktijdige, benaderende 95%-bootstrapband. Die band behandelt
de 27 componenten samen en gebruikt 2000 herhalingen met onafhankelijk
geresamplede shots in Aer en hardware.

Bij de ruimere gevoeligheidscontrole met ook resampling van de matched
twirlparen blijven **5 componenten** buiten de gelijktijdige band.
Dit zijn indices 4,5,12,14 en 24 (0..17: Z; 18..26: onsite ZZ).
De hardware-spin-RMSE minus de Aer-spin-RMSE is **0.1550**; de puntgewijze
95%-interval met deze twirl-resampling is ongeveer **[0.1125, 0.2008]**.
Dit is een modelsimulatie/hardwareverschil, geen mitigationwinst of voordeel.

Deze intervallen omvatten geen drift tussen jobs of onzekerheid in de
kalibratie. De uitspraak geldt voor dit meetpunt en deze data.
Beide bootstrapvarianten hadden 2000 geldige herhalingen zonder uitval.
De gezamenlijke bandradius was bij 1000/2000 herhalingen 0.1836/0.1836
(vaste twirls) en 0.2461/0.2500 (twirlgevoeligheid).

## Shot-resolutie is geen convergentiecertificaat

Bij de eerste 8/16/32/64 shots PER twirl (totaal 64/128/256/512) was de
Aer-spin-RMSE respectievelijk 0.2966, 0.3132, 0.2985 en 0.2676.
Deze deelreeksen zijn genest en niet onafhankelijk. Een halve-batchdiagnose
heeft een maximale ongecorrigeerde puntgewijze z-waarde van 3.87. Daarom
geen claim dat alle simulatorgemiddelden met 512 shots nauwkeurig geconvergeerd
zijn; onafhankelijke herhalingen zouden dat verder moeten toetsen.
De primaire vergelijking gebruikt alle 512 shots en de beschreven gezamenlijke
onzekerheidsband, niet alleen de gunstigste deelreeks.

## Wat weten we over het model?

- Alle acht noise-off circuits matchen de exacte Pauli-referentie tot
  maximaal 2.2649e-14. Mapping, uitleesmaskers en 1008 CZ-gates blijven behouden.
- De 80 gebruikte native gate/wire-entries in de latere timingsnapshot
  hebben exact dezelfde gerapporteerde gatefouten en duren als de vroege
  volledige kalibratie. Dat controleert nog niet de latere T1/T2-waarden.
- Van de 62 gebruikte X/SX/CZ-noisekanalen hebben zes X/SX-kanalen op de
  fysieke qubits 102,104,115 iets grotere modelinfideliteit dan de apart
  gerapporteerde gatefout. De T1/T2-relaxatie alleen ligt daar al boven die
  fout, zodat Aer geen extra depolariserende fout toevoegt. Grootste absolute
  afwijking ongeveer 6.94e-5 per gate. Geen T2-waarden zijn afgeknipt.
- Idle-gap-relaxatie, coherente/contextafhankelijke fouten, crosstalk,
  leakage, initialisatiefout en drift ontbreken nog. De huidige vergelijking
  bepaalt NIET welke daarvan het waargenomen verschil veroorzaakt.

## Tijd, bewaren en vervolg

Aer.run plus resultaten ophalen kostte samen **760.3 seconden (12.7 minuten)**
op twee CPU-threads. Dit sluit imports, modelopbouw, ideale controles,
schijfopslag en analyse uit. **Nieuw QPU-verbruik: 0 seconden.**

De physics-werkwijze heeft geleid tot een vooraf vastgelegd protocol,
gescheiden steekproef- en modelonzekerheid, 23 unit tests, broncodekopieen,
invoer- en uitvoerhashes en een onafhankelijke bit-gebaseerde controle van de
fysieke observabelen. Alle ruwe bitstrings en eerdere hardwaredata zijn bewaard.
`COMPLETION.json` is de definitieve status; het historische `run_summary.json`
registreert het eerdere moment waarop de analyse nog moest starten.

Volgende begrensde stap: een expliciet idle-aware schema uit de opgeslagen
gateduren afleiden, de aannames vergelijken met de beschikbare hardwaretiming,
en de gevoeligheid voor de toegevoegde idle-relaxatie testen. Behoud deze
basismodelrun als controle. Niet veronderstellen dat dit de volledige afwijking
oplost; niet blind ruis opschalen totdat hetzelfde meetpunt past. Nieuwe
mitigationkeuzes moeten vervolgens op aparte controlepunten worden gevalideerd.
