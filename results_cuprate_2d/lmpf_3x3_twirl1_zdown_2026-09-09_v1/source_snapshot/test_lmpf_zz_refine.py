import json, tempfile, unittest
from pathlib import Path
from lmpf_2d.canonical_chi256 import resource_estimate
from lmpf_2d.portable_archive import pack
from scripts.restore_archives import run as restore_run


class ZZRefinementTests(unittest.TestCase):
    def test_resource_bound(self):
        result = resource_estimate()
        self.assertEqual(result['real_float64_state_bytes'], 22089984)
        self.assertEqual(result['chain_flops_upper_bound'], 2769572160)
        self.assertEqual(result['chain_peak_elements'], 262144)
        self.assertLess(result['chain_flops_upper_bound'], 3e9)
        self.assertGreater(result['chain_flops_upper_bound'], 2e9)
        self.assertEqual(resource_estimate(2, 256)['bond_upper_bounds'], [1, 4, 1])

    def test_split_archive_and_exact_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / 'sample.npz'
            expected = bytes(range(256)) * 64
            target.write_bytes(expected)
            result = pack(root, ['sample.npz'], part_bytes=64)
            self.assertEqual(result['already_present'], 1)
            manifest = json.loads((root / 'archive/manifest.json').read_text())
            parts = manifest['objects'][0]['parts']
            self.assertGreater(len(parts), 1)
            self.assertTrue(all(part['bytes'] <= 64 for part in parts))
            target.unlink()  # Only this generated temporary fixture.
            self.assertEqual(restore_run(root, restore=True)['restored'], 1)
            self.assertEqual(target.read_bytes(), expected)
            target.write_bytes(b'mismatching temporary fixture')
            with self.assertRaises(FileExistsError):
                restore_run(root, restore=True)
            self.assertEqual(target.read_bytes(), b'mismatching temporary fixture')
            with self.assertRaises(FileExistsError):
                pack(root, ['sample.npz'])

    def test_archive_path_and_size_guards(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                pack(root, ['../outside'])
            with self.assertRaises(ValueError):
                pack(root, ['sample.npz'], part_bytes=10_000_000)
            self.assertFalse((root / 'archive').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
