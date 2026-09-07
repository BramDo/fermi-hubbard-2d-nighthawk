# 6x6-hardwaretest: klaar, geen aangetoonde kwaliteitswinst

Job `daf6foe42tqs73avhoeg` op Nighthawk `ibm_phoenix` is DONE.
IBM rapporteert 7 QPU-seconden, onder de bevestigde limiet van 15 seconden.
De job stond ongeveer 181 seconden op RUNNING; 7 seconden is geen end-to-endtijd.
Alle 76 invoercircuits en 38.912 shots zijn geverifieerd en bewaard.

Het compacte circuit duurt met de verse kalibratie ongeveer 81-82 microseconden,
tegenover 123-124 microseconden voor het origineel. Beide behouden 20.736 CZ-poorten.
De proef heeft geen fysische termen, interacties of tijdstappen weggelaten.

## U8-puntschattingen na readout + TFLO

| Circuit | N | RMS lading | RMS spin | RMS doublons |
|---|---:|---:|---:|---:|
| Origineel | 31.396 | 0.084 | 0.092 | 0.051 |
| Compact | 31.231 | 0.109 | 0.126 | 0.064 |

Dit zijn afstanden tegenover de niet-gecertificeerde klassieke chi64-referentie.
De compacte puntschattingen zijn slechter, maar de conditionele 95%-intervallen
voor de verschillen omvatten nul. Geen statistisch bewezen algemene verslechtering.

Beide versies falen de vooraf vastgelegde onafhankelijke U0-TFLO-holdoutscreen.
Bij T=.4 is de TFLO-spinfout tegenover exact U0 ongeveer .390 origineel en .359
compact; de bijbehorende bovengrenzen zijn .420 en .400, ruim boven de eis .05.
Op dit U0-controlepunt zijn de readout-gecorrigeerde lading en doublons voor
compact juist slechter; hun conditionele gepaarde winstintervallen liggen onder nul.
Voor spin is daar geen significante readoutwinst zichtbaar.

Ook de controle zonder U8-doelhardware-input blijft beter in deze lokale profielen:
ongeveer .029/.058/.011 RMS voor beide armen. Een gunstige TFLO-uitkomst alleen
is dus opnieuw geen bewijs van teruggewonnen interactiedynamica.

Conclusie: deze compactie levert kortere circuits, maar geen aangetoonde betere
6x6-resultaten. De TFLO-uitkomsten blijven DIAGNOSTIC_UNVALIDATED. De proef
is geen quantum-advantagebewijs en isoleert de foutoorzaak niet. De grote
resterende CZ-belasting blijft een aandachtspunt, geen hier bewezen oorzaak.

Geen tweede job gestart. De eenmalige toestemming is verbruikt.
Volledige profielen, negatieve kansen, onzekerheden en controles staan in
`analysis/RAPPORT.md` en `analysis/summary.json`. Alle ruwe data en originele
circuits blijven behouden; verliesvrije spiegels worden afzonderlijk geverifieerd.
De physics- en veilige-API-skills borgden protocol, budgetcontrole en archivering.
