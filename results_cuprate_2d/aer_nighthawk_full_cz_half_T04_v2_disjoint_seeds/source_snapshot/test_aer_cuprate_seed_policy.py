"""Guard Aer run-level seed spacing, including the per-shot addition."""
import unittest
import numpy as np
import aer_cuprate_cz_half_v2 as v2
from aer_seed_overlap_diagnostic import probe

class SeedPolicyTests(unittest.TestCase):
    def test_all_256_new_shot_seeds_unique(self):
        seeds = [v2.seed_for(m,t)+s for m in range(2) for t in range(8) for s in range(16)]
        self.assertEqual(len(set(seeds)), 256)
        self.assertTrue(all(0 <= s < 2**32 for s in seeds))
    def test_no_overlap_with_prior_screen_ranges(self):
        prior = set()
        for base, count in [(2026090590,64),(2026090700,16),(2026090800,16),
                            (2026091000,16),(2026091100,16),(2026091300,16),(2026091400,16)]:
            prior.update(base+t+s for t in range(8) for s in range(count))
        fresh = {v2.seed_for(m,t)+s for m in range(2) for t in range(8) for s in range(16)}
        self.assertFalse(prior & fresh)
    def test_invalid_model_or_twirl_rejected(self):
        for m,t in [(-1,0),(2,0),(0,-1),(0,8)]:
            with self.assertRaises(ValueError):
                v2.seed_for(m,t)
    def test_empirical_overlap_one_thread(self):
        self.assertLess(probe(1)['adjacent_shift_max_error'], 1e-12)
    def test_empirical_overlap_two_threads(self):
        self.assertLess(probe(2)['adjacent_shift_max_error'], 1e-12)

if __name__ == '__main__':
    unittest.main()
