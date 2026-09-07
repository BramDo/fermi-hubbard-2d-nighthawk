# Experimenten en theorie: vindwijzer

Alle paden hieronder zijn relatief aan results_cuprate_2d, tenzij anders
vermeld. Dit is een thematische ingang; source_copy_manifest.json is het
volledige bestandsoverzicht. Oudere Fez/Fire Opal-resultaten zijn context.

| Thema | Archief of bron | Interpretatie |
|---|---|---|
| Volledige fermiontekens | fermionic_dynamics_2026-09-05 | kleine exacte controles |
| Routing/fSWAP | fermionic_mapping_2026-09-05 | resources; niet vanzelf nauwkeurigheid |
| Exacte pilot | fermionic_pilot_3x3_2026-09-05 | klassiek controleerbaar |
| Exacte 3x3 opnieuw berekend | exact_3x3_recomputed_2026-09-07_v1 | volledige sector 15.876 toestanden; T=0.1/0.2/0.4; 64 controles geslaagd |
| Ruissimulaties | aer_nighthawk_* en aer_readout_tflo_zne_* | opgeslagen ruismodel; geen hardwarebewijs |
| Seed-audit | aer_seed_overlap_* | gecorrigeerde statistische afhankelijkheid |
| Readout/CZ-folding | hardware_readout_cz_folding_3x3_2026-09-06 | aparte pilot |
| Eerste volledige 6x6-meting | hardware_readout_cz_folding_6x6_2026-09-06 | aparte familie en mitigatie |
| 5x5 hardwarecontrole | hardware_controls_5x5_2026-09-06_v1 | voorbereiding en U0 |
| TFLO plus DD | hardware_tflo_dd6_2026-09-06_v1 | 8QPU s; holdouts mislukt |
| Laatste paired hardware | hardware_compact_tflo_2026-09-07_v1 | 7QPU s; DD uit; holdouts mislukt |
| Symbolische compactie | quantum_compact_tflo_2026-09-07_v1 | compilercontrole |
| Klassieke MPS | classical_full_6x6_mps_T04_v1 en *_chi64_v1 | niet-geconvergeerde referenties |
| Snelle eenvoudige schatters | classical_mean6_timing_2026-09-06_v1 | context voor target-input-ablatie |
| Sectorcontroles | mitigation_6x6_sector_comparison_2026-09-06_v1 | geen achteraf verborgen N-vervanging |
| Ancilla/PA | pa_* | resourceproeven, ook negatieve uitkomsten |
| Bonsai | bonsai_* | gecontroleerde alternatieve mappings |
| qDRIFT | qdrift_first_pilot_v1 | afzonderlijke benadering/foutbudget |
| Spin-correlaties | spin_correlations_T04_2026-09-06_v1 | afzonderlijke onderzoeksvraag |
| Google-conversie | google_conversion_2026-09-07_v1 | lokale Z/ZZ-data; modellen verschillen |

Rootbestanden *_PROTOCOL.md leggen hypotheses, conventies en budgetten vast.
Rootbestanden test_*.py/verify_*.py bevatten de controles; audit_*.py de
resource- en validatieanalyses. HANDBOOK.md verbindt die aan de theorie.
De historische output/wordpress_2d_cuprate_series is serie2, niet serie3.
