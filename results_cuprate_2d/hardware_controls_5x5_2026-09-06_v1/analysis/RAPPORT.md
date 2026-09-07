# Hardwarecontrole: voorbereiding en5x5 U=0

Job: daer9j5nj4cs73afhofg. Maximaal5 QPU-seconden; providergebruik: {'qpu_charge_time_seconds': 3, 'status': 'complete'}.
12 circuits x512 shots:6144 totaal. Geen U8-hardware, ZNE, PEC, qDRIFT, TFLO-fit of postselectie.
5x5 heeft22 deeltjes,6x6 heeft32. Spin=n_up-n_down. Alle ruwe bits zijn behouden.

| Controle | Analyse | N | N95%-interval | RMS lading | RMS spin | RMS doublon |
|---|---|---:|---|---:|---:|---:|
| prep5 | raw | 21.93555 | [21.89062, 21.97854] | 0.01646 | 0.02221 | 0.00772 |
| prep5 | readout | 21.89686 | [21.84482, 21.95267] | 0.00641 | 0.00588 | 0.00382 |
| prep6 | raw | 31.88184 | [31.82810, 31.93557] | 0.01532 | 0.02373 | 0.00850 |
| prep6 | readout | 31.87201 | [31.80298, 31.93498] | 0.00701 | 0.00602 | 0.00312 |
| flo5_T04 | raw | 24.84521 | [24.68549, 25.00051] | 0.23939 | 0.33957 | 0.09585 |
| flo5_T04 | readout | 24.86116 | [24.69818, 25.02150] | 0.23891 | 0.33991 | 0.09572 |

De U=0-vergelijking gebruikt de exacte IDEALE EINDIGE-CIRCUITreferentie; de afzonderlijke continue-tijdreferentie en Trotterconvergentie staan in references.json.
Onafhankelijke native uitleesmatrixinversie versus Pauli-methode: maximaal 3.33e-16 afwijking.
De intervallen omvatten shot- en onafhankelijke kalibratieonzekerheid, niet drift, gecorreleerde SPAM of modelbias.
De vooraf vastgelegde screen is diagnostisch en geen nauwkeurigheidscertificaat. Een correct totaal N alleen bewijst geen correcte lokale fysica.
Als voorbereiding goed is maar U0-dynamica faalt, wijst dat op fouten tijdens de diepere uitvoering; het is geen bewijs welke afzonderlijke ruisbron verantwoordelijk is.
Een geslaagde U0-controle bewijst nog geen nauwkeurige U8- of6x6-dynamica. Daarvoor is nieuwe toestemming en aparte validatie nodig.
Physics- en veilige-API-skills stuurden onafhankelijke referenties, vaste analyse, budgetgrens en eenmalige indiening.
