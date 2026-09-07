import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import continue_fermionic_6x6_chi64 as c


class ContinuationTests(unittest.TestCase):
    def test_fixed_limits(self):
        self.assertEqual((c.KERNEL_LIMIT, c.PROCESS_LIMIT, c.RSS_LIMIT),
                         (600., 650., 2 * 1024**3))

    def test_kernel_stop_independent_of_process(self):
        self.assertEqual(c.limit_reason(620., 600.01, 10), 'KERNEL_TIMEOUT')

    def test_process_stop_with_no_kernel_marker(self):
        self.assertEqual(c.limit_reason(650.01, None, 10), 'PROCESS_TIMEOUT')

    def test_memory_stop_and_no_false_stop(self):
        self.assertEqual(c.limit_reason(1., None, c.RSS_LIMIT + 1), 'RSS_LIMIT')
        self.assertIsNone(c.limit_reason(650., 600., c.RSS_LIMIT))

    def test_cpu_environment(self):
        self.assertEqual(os.environ['CUDA_VISIBLE_DEVICES'], '')
        self.assertEqual(os.environ['OPENBLAS_NUM_THREADS'], '1')
        self.assertEqual(os.environ['OMP_NUM_THREADS'], '1')

    def test_exclusive_write_preserves_first_value(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / 'value.json'
            c.write_once(path, {'first': 1})
            with self.assertRaises(FileExistsError):
                c.write_once(path, {'second': 2})
            self.assertEqual(json.loads(path.read_text()), {'first': 1})

    def test_refuse_driver_with_existing_output(self):
        with tempfile.TemporaryDirectory() as name, patch.object(c, 'OUT', Path(name)):
            with self.assertRaises(FileExistsError):
                c.driver()

    def test_full_site_comparison(self):
        zero = {'physical_means': np.zeros((36, 3)), 'number_error': 0.}
        row = {'physical_means': np.tile([.01, -.02, .03], (36, 1)), 'number_error': 0.}
        diff = c.difference(row, zero)
        np.testing.assert_allclose(diff['rms_charge_spin_doublon'], [.01, .02, .03])
        np.testing.assert_allclose(diff['max_abs_charge_spin_doublon'], [.01, .02, .03])
        self.assertFalse(diff['heuristic_screen_pass'])
        self.assertTrue(c.difference(zero, zero)['heuristic_screen_pass'])

    def test_number_gate(self):
        left = {'physical_means': np.zeros((36, 3)), 'number_error': .1}
        self.assertFalse(c.difference(left, left)['heuristic_screen_pass'])

    def test_comparison_rejects_wrong_size_or_nonfinite(self):
        row = {'physical_means': np.zeros((9, 3)), 'number_error': 0.}
        with self.assertRaises(ValueError):
            c.difference(row, row)
        row['physical_means'] = np.full((36, 3), np.nan)
        with self.assertRaises(ValueError):
            c.difference(row, row)


if __name__ == '__main__':
    unittest.main()
