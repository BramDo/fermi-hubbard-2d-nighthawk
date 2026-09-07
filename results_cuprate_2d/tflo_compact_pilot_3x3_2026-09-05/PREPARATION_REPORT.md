# Compacte TFLO-hardwarepilot: voorbereid, niet ingediend

0 nieuwe QPU-seconden. Een nieuwe expliciete toestemming blijft vereist.

Zelfde 3x3-model met volledige fermiontekens, t, t-prime/t=-0.25, U/t=8, 18 logische qubits, twee Trotterstappen en dezelfde fysieke mapping op ibm_phoenix. 10 instellingen x 8 twirls x 64 shots = 5120 shots; 512 per instelling, inclusief U=0-kalibratie.

Alleen de al gevalideerde een-qubit-opschoning verandert de circuits: 42.4% minder X/SX, diepte 623-637, nog 1008 CZ per circuit. Geen hardwareverbetering gemeten.

Analyse nu vooraf vastgelegd: filtertolerantie 1, minimum 32, vaste ridge 0.001. De keuze komt uit de eerdere verkenning; de oude strikte primaire analyse blijft mislukt bewaard. Fit opnieuw uitsluitend op zes nieuwe U=0-trainingspunten, twee U=0-validatiepunten buiten de fit. Geen hergebruik van oude fitcoefficienten en geen nieuwe filterkeuze op U=8.

Verplicht vergelijken met raw, filter-only en een vooraf opgeslagen geheel klassieke U=0-FLO-voorspelling. Rapporteer paired-gain-intervallen met 400 twirl/shot-bootstrapreplicaties en U=0-refits. Geen claim van extra winst wanneer het interval nul bevat. Bij onvoldoende samples stopt de primaire fit; geen automatische filteraanpassing of herhaling.

448 nieuwe lokale controles geslaagd, waaronder alle 80 bound-QPY-herlaadtests. 32 oorspronkelijke artifacthashes gecontroleerd. De 138 eerdere ideale-equivalentiechecks zijn via hun hashes geverifieerd, niet opnieuw gesimuleerd.

Deze voorbereiding heeft geen submissionfunctie. De oude runner en indieningsblokkering zijn onaangeroerd. Voorstel na toestemming: precies een job, max_execution_time=5, geen sessie/batch/retry/backendwissel. Eerst een aparte actuele read-only tijdsraming; onbekende subjoboverhead kan de job laten afbreken.

Vergelijkingen met de vorige job zijn beschrijvend door mogelijke hardwaredrift. Referentie: hetzelfde eindige Trottercircuit, niet exact continue dynamica. Deze kleine klassiek oplosbare pilot kan geen quantum advantage bewijzen.
