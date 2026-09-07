# Bonsai 6x6: vaste model- en circuitvergelijking

Alleen lokaal; geen nieuwe QPU-run. Zelfde t,t-prime,U,fermiontekens,T=0,4 en oorspronkelijke fysieke eventvolgorde.
72 encodingqubits, geen extra encoding-ancillas. Voorbereiding bestaat alleen uit X-poorten.
Pariteitsnetwerken zijn op bestaande CZ-verbindingen gebouwd, zonder SWAP-router.
Steiner-qubits blijven quantumdata en worden volledig terughersteld.

7 tests slagen, inclusief volledige2x2/2x3-dynamica, Majorana-algebra en GF2-uitlezing.
Geen volledige72-qubit-statevector berekend.

| Volledig circuit, een controle-twirl | CZ | CZ-lagen | Diepte | Geschatte duur (us) |
|---|---:|---:|---:|---:|
| Bestaande compacte variant | 15400 | 564 | 2030 | 72.252 |
| original72_naive_twirl | 23478 | 9433 | 33819 | 1052.384 |
| original72_anneal9_twirl | 18353 | 7168 | 25382 | 816.464 |
| original72_anneal27_twirl | 18223 | 6904 | 25065 | 777.376 |
| rectangle72_naive_twirl | 23302 | 8575 | 29895 | 965.532 |
| rectangle72_anneal9_twirl | 14338 | 5080 | 17705 | 586.812 |
| rectangle72_anneal27_twirl | 14912 | 5624 | 19282 | 639.060 |

Duren omvatten voorbereiding en uitlezing, niet reset/rep_delay/queue. Opgeslagen kalibratie, geen live fidelitymeting.
De annealingkostenfunctie is uitsluitend een zoekproxy. Minder CZ is niet automatisch minder diepte.
Andere fysieke subset is apart vermeld; daarmee is een kwaliteitsvergelijking niet automatisch hardwaregematcht.

## Uitlezing en vervolg

Ruwe bits zijn encoded Bonsai-bits, geen directe fermionbezettingen. Corrigeer eerst het vastgelegde fysieke readout-X-masker en decodeer vervolgens de GF2-pariteiten.
Lading en doublons zijn op kleine systemen gecontroleerd. De bestaande hardware-readoutmitigatie moet nog aan de nieuwe pariteitsobservabelen worden aangepast.
Geen qDRIFT of nieuwe klassieke modelbenadering toegepast. De bestaande ideale eindige-circuitreferentie blijft het doel.
Geen complete ZNE-batch, verse calibratie/budgetcontrole of hardware-autorisatie aanwezig.

## Verificatie en afwijkingen

Geen fysische vereenvoudiging. Bonsai is aangepast aan de opgeslagen Nighthawk-grid, niet aan Boston heavy-hex.
Lokale parity-tree-synthese en equal-visit kostenfunctie zijn implementatiekeuzes voor dit vaste Trotterdoel.
De physics-skill stuurde de onafhankelijke teken-, unitairiteits-, voorbereidings- en uitleescontroles.
Bronnen: https://arxiv.org/abs/2212.09731 en https://arxiv.org/html/2608.25024 .
