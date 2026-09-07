# Exacte 3x3 Hubbard-berekening

Opnieuw lokaal uitgerekend; geen QPU gebruikt. De oude resultaten zijn niet overschreven.

Model: 3x3 open, 18 fermionmodi, N_up=N_down=4; een gat op middensite 4. t=1, t_prime=-0.25, U=8, mu=0. Modeltijd in hbar/t.

De volledige vaste sector telt C(9,4)^2 = 15.876 toestanden. We berekenen psi(T)=exp(-i H T) psi(0), zonder MPS-truncatie of Trotterbenadering. Exact betekent hier numeriek exact binnen de gecontroleerde drijvende-kommaprecisie, niet een symbolische formule.

## Waarden en gemeten tijden

| Modeltijd | N | Gemiddeld D/site | Spinprofiel-RMS | Evolutiekern, mediaan 5x (s) |
|---|---:|---:|---:|---:|
| 0.1 | 8.000000000000 | 0.016222765199 | 0.902815544199 | 0.048035 |
| 0.2 | 8.000000000000 | 0.049209299932 | 0.811290350214 | 0.063806 |
| 0.4 | 8.000000000000 | 0.064354264250 | 0.685165729385 | 0.092092 |

Hamiltoniaan opbouwen: 1.316148 s; basis: 0.050678 s. De evolutietijden hierboven sluiten opbouw, imports en onafhankelijke controles uit.

T=0.2 reproduceert de eerdere volledige fermionpilot. T=0.4 is een extra exacte kleine-roosterreferentie op de modeltijd van de latere 6x6-studie; het is niet dezelfde roosteropgave.

## Lokale waarden bij T=0.2

| Site (x,y) | Lading | Spin n_up-n_down | Doublon |
|---|---:|---:|---:|
| 0 (0,0) | 0.9998240289 | 0.8753726275 | 0.0570605541 |
| 1 (1,0) | 0.9641156652 | -0.8428695201 | 0.0533686984 |
| 2 (2,0) | 0.9998240289 | 0.8753726275 | 0.0570605541 |
| 3 (0,1) | 0.9641156652 | -0.8428695201 | 0.0533686984 |
| 4 (1,1) | 0.1442412238 | -0.1300124296 | 0.0011666897 |
| 5 (2,1) | 0.9641156652 | -0.8428695201 | 0.0533686984 |
| 6 (0,2) | 0.9998240289 | 0.8753726275 | 0.0570605541 |
| 7 (1,2) | 0.9641156652 | -0.8428695201 | 0.0533686984 |
| 8 (2,2) | 0.9998240289 | 0.8753726275 | 0.0570605541 |

## Lokale waarden bij T=0.4

| Site (x,y) | Lading | Spin n_up-n_down | Doublon |
|---|---:|---:|---:|
| 0 (0,0) | 1.0037511609 | 0.7592053195 | 0.0819059333 |
| 1 (1,0) | 0.8975054335 | -0.6686182867 | 0.0609784878 |
| 2 (2,0) | 1.0037511609 | 0.7592053195 | 0.0819059333 |
| 3 (0,1) | 0.8975054335 | -0.6686182867 | 0.0609784878 |
| 4 (1,1) | 0.3949736225 | -0.3623481313 | 0.0076506938 |
| 5 (2,1) | 0.8975054335 | -0.6686182867 | 0.0609784878 |
| 6 (0,2) | 1.0037511609 | 0.7592053195 | 0.0819059333 |
| 7 (1,2) | 0.8975054335 | -0.6686182867 | 0.0609784878 |
| 8 (2,2) | 1.0037511609 | 0.7592053195 | 0.0819059333 |

## Exact circuit is een andere referentie

Het bewaarde 18-qubit circuit is ook zonder ruis opnieuw doorgerekend. Zijn eindige productformule benadert de continue Hamiltoniaandynamica. Het verschil hieronder is Trotterbias, geen hardwarefout.

{
  "charge": {
    "rms": 0.0010991115449050747,
    "max_abs": 0.0026338091373178663
  },
  "spin_z": {
    "rms": 0.00583531340245067,
    "max_abs": 0.006320533058784106
  },
  "double_occupancy": {
    "rms": 0.0027751688893462244,
    "max_abs": 0.0035029145957671606
  }
}

## Opgeslagen bestanden

- observables.json: alle lokale waarden en samenvattingen, inclusief T=0 en T=0.1.
- state_vectors.json.gz: sectorbasis en volledige complexe toestanden, verliesloos gecontroleerd.
- config.json, source_sha256.json, summary.json: instellingen, herkomst en afzonderlijke tijdmetingen.
- checks.json en VERIFICATION.md: onafhankelijke numerieke controles.

Deze 3x3-opgave is klassiek exact oplosbaar; dit is geen quantum-advantage-bewijs. De 6x6-resultaten worden hierdoor niet automatisch gevalideerd.

Hele verse Python-worker inclusief imports, drie tijdpunten, herhalingen, alle controles en opslag: 14.993684 s; exclusief de Windows/WSL-launcher. Dit is niet de korte evolutiekern alleen.
