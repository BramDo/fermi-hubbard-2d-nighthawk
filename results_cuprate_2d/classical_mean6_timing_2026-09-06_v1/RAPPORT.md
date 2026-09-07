# Klassieke controle vanaf nul: 0,114 s rekenen; 1,61 s inclusief opstart

De zes exacte U=0-trainingsprofielen en hun gemiddelde zijn in vijf verse
Python-processen opnieuw berekend. De mediane rekentijd is 0,114 seconde.
Inclusief Windows->WSL->Python-opstart, controles, JSON-uitvoer en terugkeer
duurt een aanroep mediaan 1,61 seconde. Geen opgeslagen trainingsantwoorden
of U=8-doelmetingen zijn gebruikt om de voorspelling te maken. Geen QPU-job.

Voor deze specifieke observabelen bij dit ene eindpunt is 150 seconden MPS-
rekentijd dus niet noodzakelijk om de eerder besproken benaderingskwaliteit
te halen. De goedkopere klassieke controle ligt dichter bij dezelfde chi64-
referentie dan de TFLO-gecorrigeerde quantumdata.

## Alle vijf metingen

| Run | Zes profielen + gemiddelde | Python tot resultaat gereed | Volledige Windows-aanroep |
|---|---:|---:|---:|
| 1 | 0,114087 s | 1,021535 s | 1,615844 s |
| 2 | 0,115768 s | 1,084709 s | 1,679670 s |
| 3 | 0,116978 s | 1,016328 s | 1,613129 s |
| 4 | 0,090986 s | 0,948946 s | 1,515130 s |
| 5 | 0,102119 s | 0,905601 s | 1,485117 s |
| Mediaan | 0,114087 s | 1,016328 s | 1,613129 s |

Spreiding volledige aanroep: 1,485-1,680 s. Dit is een waargenomen bereik,
geen betrouwbaarheidsinterval. Verse processen, maar geen geleegde OS-cache.
De klok voor de volledige aanroep stopt na ontvangst van stdout/stderr en
proces-einde; het schrijven van deze auditbestanden en rapportredactie valt
erbuiten. Per aanroep zitten de numerieke interne controles er wel in.

Machine: AMD Ryzen 5 3500U, 4 cores / 8 logische processors, CPU-only,
Ubuntu-Preview-C en de bestaande Qiskit-venv. BLAS/OMP op een thread.
Andere systeembelasting is niet geisoleerd; gemeten CPU-belasting vooraf 13%.
De vijf benchmarkruns zelf zijn niet parallel uitgevoerd. Tests en vergelijking
met bewaarde antwoorden gebeurden buiten de vijf rekentijdmetingen.

## Kwaliteit tegenover dezelfde chi=64-referentie

| Methode | N | RMS lading | RMS spin | RMS doublons |
|---|---:|---:|---:|---:|
| Opnieuw berekend klassiek trainingsgemiddelde | 32,000 | 0,029306 | 0,057594 | 0,011377 |
| Eerdere hardware + readout + TFLO + DD | 32,078 | 0,071702 | 0,091393 | 0,051587 |

Alle nieuw berekende trainingsprofielen zijn exact gelijk aan de eerder
opgeslagen dubbelprecisie-profielen (maximaal verschil 0). Ook de vijf
voorspellingen en de gereproduceerde RMS-afstanden verschillen onderling niet.
Dit betreft absolute RMS-afstanden, geen procentuele fouten of exacte
foutgrenzen. Spin is n_up-n_down, niet S_z.

## Wat betekent dit voor de vergelijking 150 tegen 8 seconden?

- De oude volledige MPS-chi64-berekening kostte 150,819 s in de kernel en
  156,905 s inclusief worker-opstart/imports, exclusief Windows/WSL-launcher.
  Zij draaide toen met andere lokale werkzaamheden tegelijk. Niet opnieuw
  gemeten in deze test.
- De klassieke benadering hierboven kost 0,114 s in de kernel en 1,613 s
  voor de volledige aanroep. Het is geen volledige U=8-MPS-simulatie.
- De eerdere quantumjob gebruikte 8 afgerekende QPU-seconden voor het hele
  pakket van training, controles, doelmetingen en kalibraties. RUNNING->DONE
  was 260,372 s. De latere analyse inclusief archiefcontrole en bootstrap
  kostte afzonderlijk 37,393 s; volledige voorbereiding en end-to-end-tijd
  zijn niet als een uniforme benchmark gemeten.

Dit zijn bewust verschillende tijdsgrenzen. De verhouding 150,819/8=18,85
mag als verhouding MPS-kerneltijd/QPU-gebruik worden genoemd, maar bewijst
niet dat de quantumcomputer de pc verslaat voor deze benaderingskwaliteit.
De huidige klassieke controle bereikt de getoonde nabijheid tot chi64 al
binnen ongeveer 1,6 seconde totale aanroeptijd.

## Beperking: geen nieuw algemeen U=8-algoritme

De zes tijden en hun gelijke gewichten zijn niet in deze timingtest aangepast.
Het gemiddelde als alternatieve U=8-voorspeller is wel achteraf gekozen, nadat
de eerdere resultaten bekend waren. Dit blijft een post-hoc controle bij een
enkel eindpunt, geen prospectief gevalideerde methode voor algemene dynamica.
Het geeft een vast profiel terug, geen voorspelling die met de gevraagde U of
doeltijd verandert. De goede overeenkomst kan elders verdwijnen.

De U=0-referenties behouden alle kwadratische hoppingtermen, inclusief t',
in precies de bestaande tweestaps-circuitvolgorde. Zij volgen 72x32 bezette
een-deeltjesorbitalen, geen exponentiele 72-qubit-statevector. De gemiddelde
profielen benaderen hier de U=8-observabelen, maar simuleren niet zelf de
interagerende U=8-toestand. MPS chi64 is bovendien niet exact gecertificeerd.
Geen vooraf afgesproken tolerantie achteraf alsnog als geslaagde validatie
gepresenteerd. Geen algemene klassieke of quantum advantage aangetoond.

## Verificatie en bewaring

Zes tests geslaagd, waaronder een onafhankelijke 2x2-many-body-statevector
bij drie tijden, zero-time, lineaire omzetting, ongeldige tijd en blokkering
van resultaatbestanden/netwerk in de worker. Elk gegenereerd covariance-
projector is gecontroleerd op Hermiticiteit, idempotentie, N=32, N_up=N_down=16
en overeenkomst met direct berekende site-observabelen.

Zie `tests.json`, `verification.json`, `independent_verification.json`,
`worker_0.json` t/m `worker_4.json`, `windows_timings.json`, `summary.json`,
`environment.json`, `source_snapshot/` en de SHA256-manifesten. Oude hardware-
en MPS-archieven zijn niet gewijzigd. De physics-skill bepaalde de expliciete
tijdsgrenzen, onafhankelijke controles en het bewaren van alle herhalingen.
