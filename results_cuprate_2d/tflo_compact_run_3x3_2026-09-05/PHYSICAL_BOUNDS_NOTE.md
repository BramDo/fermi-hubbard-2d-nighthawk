# Fysische grenscontrole van de compacte TFLO-uitkomst

Bron: de ongewijzigde `primary_analysis/results.json`, job
`dae5gat1ierc738lmg10`. De code rapporteerde deze grensoverschrijding al
in `out_of_bounds_count`; deze notitie maakt haar ook in woorden expliciet.

Bij U/t=8 en tijd T=0.2 is de TFLO-puntschatting van de dubbele bezetting
op site 4 (nulgebaseerd) **-0.0194785365**. De fysisch toegestane band is
[0,1]. Het 95%-sampling/bootstrapinterval is [-0.0374874095, 0.0370992265]
en bevat nul. Op T=0.4 zijn geen TFLO-puntschattingen buiten de controlebanden.

De schatting is niet geclipt en de fit is niet aangepast: dat was vooraf
vastgelegd. Een negatieve doublonwaarde is geen fysische negatieve kans,
maar een onfysische uitkomst van de niet-begrensde mitigatieschatter. Het
interval dat nul bevat bewijst niet dat de reconstructie verder juist is.

De vooraf gekozen globale MSE-toets blijft onveranderd. TFLO verbetert
tegenover raw, maar niet aantoonbaar tegenover de klassieke U=0-controle.
Deze grensoverschrijding is een extra reden om geen volledig fysische,
foutvrije of quantum-advantage-reconstructie te claimen.
