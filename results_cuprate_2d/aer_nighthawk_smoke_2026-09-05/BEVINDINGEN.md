# Aer met opgeslagen Nighthawk-kalibratie: eerste proef geslaagd

De bestaande 3x3 Hubbard-route kan lokaal met een benaderend, fysiek gemapt
`ibm_phoenix`-ruismodel worden uitgevoerd. Acht ruisvolle shots van U/t=8,
T=0.4, twee Trotterstappen en twirl 0 draaiden in **13.1073 seconden**
(Aer.run plus resultaat ophalen; zonder imports, voorbereiding en controles).
Er is **0 seconde QPU-budget** verbruikt en geen IBM-netwerkverzoek gedaan.

## Wat is daadwerkelijk behouden en gecontroleerd?

- Exact het reeds ingediende native circuit, uit `provider_inputs` van job
  `dae5gat1ierc738lmg10`, met fermiontekens en t, t-prime en U.
- 1008 CZ, 1678 SX, 550 X, 2459 RZ, 18 metingen; diepte 630.
- Fysieke mapping: [112,113,114,115,116,117,118,119,109,108,107,106,
  105,104,103,102,101,111]. Deze wires EN hun foutparameters zijn samen
  hernummerd naar 0..17; er wordt geen 120-qubit statevector gemaakt.
- Alle gebruikte verbindingen komen voor in de opgeslagen coupling map.
  Alle 62 verschillende gebruikte X/SX/CZ-gate/wire-combinaties en alle
  18 uitleeskanalen hebben gemapte, niet-triviale ruis.
- Met ruis uit: maximale afwijking van de 27 Pauli-observabelen ten opzichte
  van de bevroren exacte circuitreferentie is 1.7542e-14; kans buiten
  Nup=Ndown=4 is 2.7347e-29. Dit valideert ook de readout-X-maskering.
- 11 unit tests controleren onder meer fysieke versus lokale uitleesfouten,
  tijdseenheden, CZ-kanaalfideliteit, CZ-omkering en foute mappings.
- Aer bevestigt 18-qubit statevector-trajectories, twee parallelle shots,
  geen hergebruik van een enkele ideale toestand voor alle metingen.

## Wat betekent dit nog niet?

Dit is een uitvoerbaarheidsproef, **geen nauwkeurigheidsresultaat**. Acht shots
zijn daarvoor te weinig (maximale standaardfout per Pauli circa 0.35).
Er is nog geen TFLO, ZNE of PEC op deze synthetische data toegepast en nog
geen gekwantificeerde overeenkomst met echte hardware aangetoond.

Het ruismodel gebruikt de volledige opgeslagen kalibratie met update
2026-09-05 10:57:12+02:00, van eerder dan de laatste hardwarejob. De latere
timingsnapshot wordt niet ongemerkt met deze oude kalibratie vermengd.
Gatefouten, gate-duur/T1/T2-relaxatie en asymmetrische uitleesfouten zijn
meegenomen. Ongeplande idle-gaps, init_error, leakage, crosstalk, coherente
fouten en drift zijn niet gemodelleerd. Dit is geen digitale kopie van de QPU.

De kalibratie mist frequenties. De automatische Aer-backendwrapper liep
daarop vast voordat er werd gesampled. De gebruikte officiele gate- en
readouthelpers ondersteunen dezelfde kanalen bij temperatuur=0, waarbij
de evenwichtspopulatie van de aangeslagen toestand nul is. Geen frequenties
zijn verzonnen en T1/T2- of gatefouten zijn niet uitgeschakeld.

## Volgende gerichte stap

Eerst een matched 512-shot Aer-pilot met dezelfde twirls, settings en
postselectie vergelijken met de bestaande ruwe hardwaredata. Pas daarna
diversere U0-kalibratiepatronen en mitigation testen. Zo controleren we of
het model de relevante hardwarefouten redelijk weergeeft, voordat we een
mitigationmethode op alleen synthetische data beoordelen.

Een lineaire extrapolatie van deze kleine proef geeft ongeveer **14 minuten
per 512-shot setting** op deze twee CPU-threads, of circa 2.3 uur voor tien
settings. Dit is een grove planningsschatting, geen gemeten volledige
benchmark; overhead, parameters, twirls en lokale systeembelasting kunnen
de tijd veranderen. Deze grotere run is niet gestart.

Broncode, protocol, exacte inputhashes, beperkte kalibratie, noisemodel,
gemapt circuit, ruwe acht bitstrings, Aer-resultaat en controles staan bij
deze proef. Alle eerdere hardwarearchieven blijven ongewijzigd.

Bron: [Aer NoiseModel-documentatie](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.noise.NoiseModel.html).
