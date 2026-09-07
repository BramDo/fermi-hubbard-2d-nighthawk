# Aer-seedcorrectie — 6 september 2026

De onafhankelijkheidsaanname in eerdere Aer-steekproeven klopt niet.
De runner gaf de acht twirls seeds van de vorm basis+twirl. In de gebruikte
Aer 0.17.2 Kraus/statevector-route krijgt een shot seed circuit.seed+shot_index
(shot nul gebruikt init_rng). Daardoor delen verschillende twirls seedbereiken.

## Bewijs en gevolg

- Officiele bron, vast op versie 0.17.2:
  https://github.com/Qiskit/qiskit-aer/blob/0.17.2/src/simulators/circuit_executor.hpp#L823-L834
- Regressie met 1q amplitude-dampingruis, 32 trajecten, opeenvolgende runseeds:
  de tweede reeks is exact de eerste reeks verschoven met een shot (maxfout 0).
  Dit is bevestigd met een en twee CPU-threads.
- De archieven met acht maal 16 trajecten hebben 23 verschillende seedlabels;
  het archief met acht maal 64 bitshots heeft 71. Dit zijn GEEN schattingen
  van het effectieve aantal onafhankelijke shots. Verschillende twirls zijn
  verschillende circuits en kunnen dezelfde toevalsreeks anders verbruiken.
- Onafhankelijke bootstrap over de twirls negeert die afhankelijkheid.
  De smalle intervallen en daarop gebaseerde significantieclaims mogen niet
  ongewijzigd worden gebruikt. De puntschattingen zijn niet automatisch fout.
- Er is ook een aparte seed-cluster-gevoeligheidsanalyse van het lineaire
  spincontrast opgeslagen. Dat is geen bewezen vervangend betrouwbaarheidsinterval.
  De volledige historische controleafwijking is nog niet verklaard.

## Betrokken, ongewijzigd bewaarde archieven

1. aer_nighthawk_512_T04_2026-09-05: Aer-intervallen en Aer-hardware-
   verschilintervallen/significantietellingen moeten opnieuw worden beoordeeld.
   De echte hardware-bitstrings en hardware-only analyse veranderen niet.
2. aer_nighthawk_components_T04_v1: componentverschillen blijven screenings-
   puntschattingen; de oude onafhankelijke bootstrapintervallen zijn voorlopig.
3. aer_nighthawk_cz_vs_1q_T04_v1: hetzelfde voor CZ-versus-X/SX-screening.
4. aer_nighthawk_full_cz_half_T04_v1: de eerste circa 19%-spinwinst en haar
   interval zijn voorlopig; gebruik de nieuwe v2 als primaire vergelijking.

Het noise-off/endianness/algebra/channel-hashbewijs in deze archieven blijft
bruikbaar. De regressie is geen bewijs dat de echte hardware door deze fout
verandert. Er is geen nieuwe QPU-job gestart.

## Gecorrigeerde herhaling

aer_nighthawk_full_cz_half_T04_v2_disjoint_seeds herhaalt exact dezelfde
fysische vraag met 128 trajecten per model, acht twirls en hetzelfde readoutmodel.
Controlseed 2026100000+1000*twirl; half-CZ 2026200000+1000*twirl.
Alle 256 per-shot seedlabels zijn verschillend en overlappen niet met de
bekende vorige studies. Geen selectie van gunstige seeds, geen extra
herhalingen op basis van significantie, geen wijziging van kalibratie.

Dit is een correctie van onze simulatie-opzet, niet een fout in Aer:
het beschreven seedgedrag is reproduceerbaar en was in onze opzet niet verwerkt.
Een geslaagde hypothetische kanaalreductie is nog geen werkende ZNE/PEC,
hardwarevoorspelling of aangetoonde quantum advantage.

Broncode en bewijs: aer_seed_overlap_diagnostic.py,
analyze_aer_seed_overlap_impact.py, test_aer_cuprate_seed_policy.py;
resultaten onder results_cuprate_2d/aer_seed_overlap_audit_2026-09-06
en results_cuprate_2d/aer_seed_overlap_impact_2026-09-06.
