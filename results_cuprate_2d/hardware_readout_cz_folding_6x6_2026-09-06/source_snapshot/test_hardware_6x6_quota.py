import unittest
from unittest.mock import patch
import run_hardware_6x6_rocz_checked as c

class QuotaTests(unittest.TestCase):
    def test_unknown_is_not_zero_or_unlimited(self):
        r=c.usage_summary({'usage_consumed_seconds':33})
        self.assertFalse(r['remaining_quota_reported'])
        self.assertNotIn('usage_remaining_seconds',r)
        self.assertEqual(r['authorized_job_cap_seconds'],15)
    def test_known_quota_below_cap_fails(self):
        for value in [0,14.9]:
            with self.assertRaises(ValueError): c.usage_summary({'usage_remaining_seconds':value})
    def test_allocation_derived(self):
        self.assertEqual(c.usage_summary({'usage_allocation_seconds':600,'usage_consumed_seconds':33})['usage_remaining_seconds'],567)
    def test_nan_or_negative_rejected(self):
        for value in [float('nan'),-1,float('inf')]:
            with self.assertRaises(ValueError): c.usage_summary({'usage_consumed_seconds':value})
    def test_submit_authority_before_files_or_provider(self):
        with patch.object(c,'checked_frozen') as check,patch.object(c,'live_gate') as live:
            with self.assertRaises(PermissionError): c.submit()
            check.assert_not_called(); live.assert_not_called()
    def test_canonical_v1_lock_shared(self):
        self.assertEqual(c.RUN,c.h.RUN)
        self.assertEqual(c.CAP,15)
if __name__=='__main__': unittest.main()

