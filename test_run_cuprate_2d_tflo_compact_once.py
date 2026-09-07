"""Local at-most-once and frozen-compact-input tests; no provider calls."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import run_cuprate_2d_tflo_compact_once as runner


class CompactOnceTests(unittest.TestCase):
    def intent(self):
        return {'tag': 'LOCAL_TEST_ONLY', 'plan_sha256': runner.PLAN_HASH,
                'options': {'max_execution_time': 5}}

    def test_flag_required_before_any_provider_call(self):
        with patch.object(runner, 'QiskitRuntimeService', side_effect=AssertionError('must not contact provider')):
            for function in (runner.prepare, runner.submit):
                with self.assertRaises(PermissionError):
                    function(False)

    def test_success_cannot_submit_twice(self):
        with tempfile.TemporaryDirectory() as folder:
            root, calls = Path(folder), []
            def send():
                calls.append(1)
                return SimpleNamespace(job_id=lambda: 'LOCAL_TEST_ONLY')
            with contextlib.redirect_stdout(io.StringIO()):
                runner.dispatch_once(root/'lock.json', root/'receipt.json', self.intent(), send)
            with self.assertRaises(FileExistsError):
                runner.dispatch_once(root/'lock.json', root/'receipt.json', self.intent(), send)
            self.assertEqual(len(calls), 1)
            self.assertEqual(runner.read(root/'receipt.json')['plan_sha256'], runner.PLAN_HASH)

    def test_lost_response_consumes_attempt(self):
        with tempfile.TemporaryDirectory() as folder:
            root, calls = Path(folder), []
            def send():
                calls.append(1)
                raise TimeoutError('synthetic lost response')
            with self.assertRaises(TimeoutError):
                runner.dispatch_once(root/'lock.json', root/'receipt.json', self.intent(), send)
            self.assertTrue((root/'lock.json').exists())
            self.assertFalse(runner.read(root/'dispatch_uncertain.json')['resubmit_allowed'])
            with self.assertRaises(FileExistsError):
                runner.dispatch_once(root/'lock.json', root/'receipt.json', self.intent(), send)
            self.assertEqual(len(calls), 1)

    def test_existing_lock_blocks_even_without_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            runner.exclusive_json(root/'lock.json', {'reserved': True})
            with self.assertRaises(FileExistsError):
                runner.dispatch_once(root/'lock.json', root/'receipt.json', self.intent(),
                    lambda: self.fail('No POST allowed'))

    def test_wrong_plan_or_cap_fails_before_lock(self):
        for key in ('plan', 'cap'):
            with tempfile.TemporaryDirectory() as folder:
                root, intent = Path(folder), self.intent()
                if key == 'plan':
                    intent['plan_sha256'] = runner.legacy.PLAN_HASH
                else:
                    intent['options']['max_execution_time'] = 6
                with self.assertRaises(ValueError):
                    runner.dispatch_once(root/'lock.json', root/'receipt.json', intent,
                        lambda: self.fail('No POST allowed'))
                self.assertFalse((root/'lock.json').exists())

    def test_frozen_compact_inputs_and_legacy_separation(self):
        plan = runner.verified_plan()
        pubs = runner.bind_inputs(plan)
        self.assertNotEqual(runner.PLAN, runner.legacy.PLAN)
        self.assertNotEqual(runner.RUN, runner.legacy.RUN)
        self.assertNotEqual(runner.PLAN_HASH, runner.legacy.PLAN_HASH)
        self.assertEqual(len(pubs), 80)
        self.assertEqual(sum(pub.shots for pub in pubs), 5120)
        for index, pub in enumerate(pubs):
            self.assertEqual(pub.shape, ())
            self.assertEqual(pub.circuit.num_clbits, 18)
            self.assertEqual(pub.circuit.count_ops()['cz'], 1008)
            self.assertEqual(pub.circuit.metadata['tflo_record_index'], index)
            self.assertEqual(pub.circuit.metadata['tflo_plan_sha256'], runner.PLAN_HASH)
            self.assertTrue(pub.circuit.metadata['cleanup_before_binding'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
