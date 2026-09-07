# TFLO 3x3: offline voorbereiding

Geen QPU-job ingediend. Geen nieuwe QPU-kosten. Bestaande cap: 5 seconden.

- Volledig t-t-prime-U model, 18 qubits, 2 vaste stappen.
- 85/85 lokale controles geslaagd.
- Vast native circuit: 1296 CZ, diepte 605.
- 6 U=0 trainingstijden, 2 aparte U=0 validatietijden, 2 U=8 validatiepunten.
- 8 expliciete twirls x 64 shots = 512 per instelling; totaal 5120 geplande shots.
- De 5120 shots zijn inclusief kalibratie, maar passen niet aantoonbaar binnen 5 seconden.

## Verificatie

Exacte FLO-covariantie vergeleken met onafhankelijke volledige Aer-statevector; native en oude logische circuits vergeleken; norm, spin/charge, twirls en klassieke meetmap gecontroleerd. Werkelijke numerieke uitkomsten staan in validation.json. De referentie is de eindige productformule, niet exacte H-dynamica.

## Grenzen

De fit mag alleen U=0 trainingsdata zien. U=8 referenties zijn uitsluitend voor validatie. De zwakke vaste ridge is niet de drietrapsregularisatie uit het paper. Symmetrieen zijn alleen gediagnosticeerd, nog niet toegepast. MESR, GPR en DD ontbreken. Bootstrap dekt geen U-afhankelijke transferbias. Er zijn geen nieuwe hardwarebitstrings.

Volgende hardwarestap vereist actuele backend- en kostencontrole, een expliciet goedgekeurd totaalbudget, behoud van gate-structuur in providerinputs en een Sampler-run die alle ruwe bitstrings per twirl archiveert.
