# Bonsai-paper: relevante volgende vergelijking

Update na de lokale vervolgproef: Bonsai is inmiddels geimplementeerd en
gecontroleerd met hetzelfde model en dezelfde eventvolgorde. Acht geteste
varianten leverden geen dieptewinst. Zie
[Bonsai-resultaat](results_cuprate_2d/bonsai_delivery_v1/RAPPORT.md).
De bronanalyse en het toenmalige voorstel hieronder blijven historisch bewaard.

Beoordeeld 2026-09-06; geen Bonsai-implementatie of hardware-run gestart.

## Bronnen en compacte bevindingen

[Esposito et al., 25 augustus 2026](https://arxiv.org/html/2608.25024),
secties II.3, IV.1-3, V.1/V.4 en appendix C:

Boston/Heron r3, heavy-hex; Bonsai met qDRIFT en geoptimaliseerde
Majoranapaar-toewijzing. De 4x4-kostenfunctie daalt circa 43%.
De grootste 6x6-run telt volgens de auteurs 2775 twee-qubitpoorten,
niet 2775 lagen; totale circuitduur 130,36 us bij T=0,125/J.
Het ingestelde qDRIFT-foutbudget is daar verruimd tot 0,1.
U/J=4, Neel-begintoestand; vergelijking (11) bevat geen aparte t-prime-term.
De antiferromagnetische structuur blijft kwalitatief zichtbaar, maar
6x6-observabelen wijken kwantitatief duidelijk van de klassieke referentie af.
Dit zijn paperclaims, geen onafhankelijke reproductie.

[Oorspronkelijk Bonsai-paper, Miller et al.](https://arxiv.org/abs/2212.09731):
een hardware-afhankelijke ternaire-boommapping kan Fock-basisstaten als
computationele basisstaten representeren. De pairing van Majoranas is essentieel.
Encoding gebruikt een qubit per fermionmodus, geen PA-ancillaregister.

## Gecontroleerde lokale uitgangssituatie

- Productiedoel: 72 modi, 32 deeltjes, t-prime/t=-0,25, U/t=8, T=0,4.
- Opgeslagen Phoenix/Nighthawk-topologie: 120 qubits, 218 CZ-edges, 10x12-grid.
- PA: 72+36=108 encodingqubits. Beste geteste volledige controle-twirl:
  21337 CZ, 3404 CZ-lagen, totale diepte10772, geschat397,968us.
- Bestaande compacte keten:15400 CZ,564 CZ-lagen, diepte2030,72,252us.
- Geen publiek Bonsai-bestand of Bonsai-export aangetroffen in de lokaal
  geinstalleerde qiskit_fermions 0.1.0 mapper-library. Dit zegt niets over andere pakketten.
- PA-resultaten en alle mislukte softwarepogingen staan bewaard onder
  results_cuprate_2d/pa_delivery_v1 en de daarin gehashte proefmappen.

## Voorstel, nog niet uitgevoerd

1. Bouw een product-preserverende Bonsai-boom op een expliciet gekozen
   verbonden set van72 Nighthawk-qubits. Kopieer geen Boston-layout of ruisgewichten.
2. Behoud het volledige t-t-prime-U-model en eerst de bestaande fysieke
   eventvolgorde: isoleer mappingwinst van veranderingen in de tijdsintegrator.
3. Optimaliseer toewijzingen van Majoranaparen op native CZ-aantal, CZ-diepte
   en geschatte duur. Controleer anticommutatie en kleine-systeem-isometrie.
4. Vertaal ook beginbezettingen, lading, spin en doublons. Gebruik niet blind
   de oude bit-naar-fermionuitlezing of readout-mitigatie.
5. Benchmark de volledige gerouteerde native circuits, inclusief voorbereiding.
   Pas daarna afzonderlijk beoordelen of qDRIFT geschikt is; dat verandert de
   benadering en vereist onafhankelijke fout- en klassieke referentiecontroles.

De paper is een motivatie voor deze vergelijking, geen bewijs dat Bonsai op
Nighthawk sneller of nauwkeuriger wordt. De PA-proef blijft als negatieve
resourcebenchmark behouden; PA als mappingfamilie is niet uitgesloten.
De physics-skill hield paperresultaten, lokale metingen en voorstellen gescheiden.
