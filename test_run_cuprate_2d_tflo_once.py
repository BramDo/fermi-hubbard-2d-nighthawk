"""Offline safety tests; no real provider object or job is constructed."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from urllib3.util.retry import Retry

import run_cuprate_2d_tflo_once as runner


class OnceTests(unittest.TestCase):
    def test_explicit_flag_required(self):
        with self.assertRaises(PermissionError):
            runner.submit(False)

    def test_success_cannot_be_repeated(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            calls=[]
            def send():
                calls.append(1)
                return SimpleNamespace(job_id=lambda:'LOCAL_TEST_ONLY')
            with contextlib.redirect_stdout(io.StringIO()):
                runner.dispatch_once(root/'lock.json',root/'receipt.json',{'tag':'local-test'},send)
            self.assertEqual(runner.read(root/'receipt.json')['job_id'],'LOCAL_TEST_ONLY')
            with self.assertRaises(FileExistsError):
                runner.dispatch_once(root/'lock.json',root/'receipt.json',{'tag':'local-test'},send)
            self.assertEqual(len(calls),1)

    def test_ambiguous_failure_keeps_lock_and_prevents_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            calls=[]
            def send():
                calls.append(1)
                raise TimeoutError('synthetic response lost')
            with self.assertRaises(TimeoutError):
                runner.dispatch_once(root/'lock.json',root/'receipt.json',{'tag':'local-test'},send)
            self.assertTrue((root/'lock.json').exists())
            self.assertFalse((root/'receipt.json').exists())
            self.assertFalse(runner.read(root/'dispatch_uncertain.json')['resubmit_allowed'])
            with self.assertRaises(FileExistsError):
                runner.dispatch_once(root/'lock.json',root/'receipt.json',{'tag':'local-test'},send)
            self.assertEqual(len(calls),1)

    def test_http_retries_disabled_for_all_known_runtime_clients(self):
        clients=[]
        for _ in range(2):
            session=SimpleNamespace(adapters={'http://':SimpleNamespace(max_retries=Retry(total=5)),
                                              'https://':SimpleNamespace(max_retries=Retry(total=5))})
            clients.append(SimpleNamespace(_session=session))
        service=SimpleNamespace(_active_api_client=clients[0],_api_clients={'a':clients[0],'b':clients[1]})
        info=runner.disable_retries(service,SimpleNamespace(_api_client=clients[1]),
                                    SimpleNamespace(_service=service))
        self.assertEqual(info['runtime_sessions_with_retries_disabled'],2)
        for client in clients:
            for adapter in client._session.adapters.values():
                self.assertEqual(adapter.max_retries.total,0)
                self.assertEqual(adapter.max_retries.connect,0)
                self.assertEqual(adapter.max_retries.read,0)

    def test_secret_bearing_output_rejected(self):
        with self.assertRaises(ValueError):
            runner.encode({'instance':'crn:TEST_ONLY'})
        with self.assertRaises(ValueError):
            runner.encode({'token':'TEST_ONLY'})

    def test_approved_frozen_plan_and_scalar_pubs(self):
        plan=runner.verified_plan()
        pubs=runner.bind_inputs(plan)
        self.assertEqual(len(pubs),80)
        self.assertEqual(sum(pub.shots for pub in pubs),5120)
        for i,pub in enumerate(pubs):
            self.assertEqual(pub.shape,())
            self.assertEqual(pub.circuit.num_clbits,18)
            self.assertEqual(pub.circuit.count_ops()['cz'],1008)
            self.assertEqual(pub.circuit.metadata['tflo_record_index'],i)


if __name__=='__main__':
    unittest.main(verbosity=2)
