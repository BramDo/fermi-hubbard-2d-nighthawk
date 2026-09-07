"""Offline boundary tests for preparation, never a hardware submission."""
import ast
import copy
import tempfile
import unittest
from pathlib import Path

import prepare_cuprate_2d_tflo_compact_pilot as pilot


class CompactPilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = pilot.read(pilot.ORIGINAL / 'manifest.json')

    def test_original_record_allocation(self):
        pilot.validate_records(self.plan)

    def test_duplicates_missing_and_extra_shots_rejected(self):
        for mutation in ('duplicate', 'missing', 'shots', 'binding'):
            plan = copy.deepcopy(self.plan)
            if mutation == 'duplicate':
                plan['records'][1] = plan['records'][0]
            elif mutation == 'missing':
                plan['records'].pop()
            elif mutation == 'shots':
                plan['records'][0]['shots'] = 128
            else:
                plan['records'][0]['parameter_values']['step_time'] = float('nan')
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                pilot.validate_records(plan)

    def test_classical_control_never_reads_U8_reference(self):
        expected = pilot.classical_predictions(self.plan['settings'])
        settings = copy.deepcopy(self.plan['settings'])
        for setting in settings:
            if setting['u_over_t'] == 8:
                del setting['reference']
        self.assertEqual(expected, pilot.classical_predictions(settings))
        self.assertEqual(len(expected), 2)
        self.assertTrue(all(len(row['pauli_prediction']) == 27 for row in expected))

    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FileExistsError):
                pilot.prepare(Path(folder))

    def test_integrity_and_path_traversal_guard(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pilot.save(root / 'data.json', {'intact': True})
            pilot.save(root / 'sha256.json', {'data.json': pilot.digest(root / 'data.json')})
            self.assertEqual(pilot.verify_tree(root), 1)
            with self.assertRaises(FileExistsError):
                pilot.save(root / 'data.json', {'changed': True})
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pilot.save(root / 'sha256.json', {'../outside.json': 'invalid'})
            with self.assertRaises(ValueError):
                pilot.verify_tree(root)

    def test_prospective_protocol_fixed_and_no_provider_import(self):
        protocol = pilot.analysis_protocol()
        self.assertEqual(protocol['sector_tolerance'], 1)
        self.assertEqual(protocol['ridge'], 0.001)
        self.assertFalse(protocol['U8_in_fit_or_filter_selection'])
        self.assertFalse(protocol['old_model_reused'])
        tree = ast.parse(Path(pilot.__file__).read_text())
        imports = [node.module or '' for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        self.assertFalse(any(name.startswith(('qiskit_ibm_runtime', 'fireopal')) for name in imports))


if __name__ == '__main__':
    unittest.main()
