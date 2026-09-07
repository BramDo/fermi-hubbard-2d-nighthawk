# Volgende compacte TFLO-pilot: klaar voor budgettoestemming

**Nog niet ingediend; extra QPU-verbruik 0 seconden.**

Voorstel: precies een job op ibm_phoenix, max_execution_time=5, 80 circuits x 64 shots = 5120 totaal; 512 per instelling inclusief kalibratie. Geen sessie, batch, automatische retry, backendwissel of extra PEC/ZNE-kalibratie.

De 42.4% X/SX-reductie is lokaal geverifieerd. De circuits houden 1008 CZ-gates; deze opschoning bewijst nog geen lagere hardwarefout. Model, mapping, tijdstippen, twirlseeds, meetvolgorde en shots zijn gelijk aan de vorige pilot.

## Actuele read-only controle

Gecontroleerd op 2026-09-05T17:38:21.910870+00:00; backend operationeel, 0 wachtende jobs op dat moment. Alle 80 circuits ISA-compatibel; 916 preflightchecks geslaagd.

Shotuitvoering inclusief reset en standaard rep_delay: 0.114237 s. De rest van de raming komt vooral van interne opstartoverhead.

| Interne subjobs | Raming inclusief overhead |
|---|---:|
| 1 | 2.114 s |
| 2 | 4.114 s |
| 3 | 6.114 s |

Het aantal interne subjobs is niet vooraf bekend. Dit is een lokale scenarioanalyse, geen providerprijsopgave of garantie dat de job onder 5 s voltooit. De voorgestelde limiet kan tot afbreken leiden; al gebruikte tijd kan meetellen. [IBM workload usage](https://quantum.cloud.ibm.com/docs/en/guides/estimate-job-run-time), [uitvoeringstijdlimiet](https://quantum.cloud.ibm.com/docs/en/guides/max-execution-time).

## Vooraf vastgelegde analyse

Tolerantie 1 is nu vast; geen nieuwe filterselectie. Minimum 32 behouden shots per instelling, ridge 0.001, uitsluitend zes nieuwe U=0-trainingspunten in de fit. Twee U=0-validatiepunten en beide U=8-doelen blijven buiten de fit. De oorspronkelijke strikte analyse en oude gegevens blijven ongewijzigd.

Verplichte vergelijking met raw, filter-only en de vooraf opgeslagen goedkope klassieke U=0-voorspelling. Primair: gepoolde Pauli-MSE op beide U=8-tijden, met 400 paired twirl/shot-bootstrapreplicaties en nieuwe U=0-fits. Geen extra winstclaim wanneer het betreffende 95%-interval nul bevat. Te weinig samples: primaire analyse stopt, zonder filterverruiming of herhaling.

## Verificatie en bewaard materiaal

448 voorbereidingschecks, 80 bound-QPY-roundtrips, 916 live preflightchecks en 25 afsluitende controles geslaagd. De eerder uitgevoerde 138 ideale-equivalentiechecks zijn via hun hashes geverifieerd; geen nieuwe statevectorrun. Alle huidige tests staan in unit_tests.txt.

Reproduceerbare uitgevoerde test:

```text
python -m unittest -v test_cuprate_2d_tflo_compact_pilot test_cuprate_2d_tflo_refinement
test_classical_control_never_reads_U8_reference (test_cuprate_2d_tflo_compact_pilot.CompactPilotTests.test_classical_control_never_reads_U8_reference) ... ok
test_duplicates_missing_and_extra_shots_rejected (test_cuprate_2d_tflo_compact_pilot.CompactPilotTests.test_duplicates_missing_and_extra_shots_rejected) ... ok
test_integrity_and_path_traversal_guard (test_cuprate_2d_tflo_compact_pilot.CompactPilotTests.test_integrity_and_path_traversal_guard) ... ok
test_no_overwrite (test_cuprate_2d_tflo_compact_pilot.CompactPilotTests.test_no_overwrite) ... ok
test_original_record_allocation (test_cuprate_2d_tflo_compact_pilot.CompactPilotTests.test_original_record_allocation) ... ok
test_prospective_protocol_fixed_and_no_provider_import (test_cuprate_2d_tflo_compact_pilot.CompactPilotTests.test_prospective_protocol_fixed_and_no_provider_import) ... ok
/home/bram/.venvs/qiskit/lib/python3.12/site-packages/uncertainties/unumpy/core.py:23: DeprecationWarning: numpy.core is deprecated and has been renamed to numpy._core. The numpy._core namespace contains private NumPy internals and its use is discouraged, as NumPy internals can change without warning in any release. In practice, most real-world usage of numpy.core is to access functionality in the public NumPy API. If that is the case, use the public NumPy API. If not, you are using NumPy internals. If you would still like to access an internal attribute, use numpy._core.numeric.
  from numpy.core import numeric
test_U8_cannot_enter_selection_or_refitting (test_cuprate_2d_tflo_refinement.RefinementTests.test_U8_cannot_enter_selection_or_refitting) ... ok
test_fixed_structure_and_CZ_trace (test_cuprate_2d_tflo_refinement.RefinementTests.test_fixed_structure_and_CZ_trace) ... ok
test_full_operator_equivalence (test_cuprate_2d_tflo_refinement.RefinementTests.test_full_operator_equivalence) ... ok
test_paired_twirl_resampling (test_cuprate_2d_tflo_refinement.RefinementTests.test_paired_twirl_resampling) ... ok
test_qpy_roundtrip_and_bound_rejection (test_cuprate_2d_tflo_refinement.RefinementTests.test_qpy_roundtrip_and_bound_rejection) ... ok
test_raw_baseline_not_forced_to_use_TFLO (test_cuprate_2d_tflo_refinement.RefinementTests.test_raw_baseline_not_forced_to_use_TFLO) ... ok
test_target_prediction_does_not_read_reference (test_cuprate_2d_tflo_refinement.RefinementTests.test_target_prediction_does_not_read_reference) ... ok

----------------------------------------------------------------------
Ran 13 tests in 8.257s

OK
```

Deze kleine klassiek oplosbare pilot toetst meetkwaliteit, geen quantum advantage. Een vergelijking met de vorige hardwarejob blijft beschrijvend door mogelijke drift. Verdere hardwareuitvoering vraagt nieuwe expliciete toestemming en een eigen exactly-once-beveiliging. De oude runner blijft afgesloten voor herhaling.
