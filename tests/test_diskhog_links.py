import os, pathlib, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cli'))
import diskhog

class HardLinkTests(unittest.TestCase):
    def test_hard_linked_data_is_counted_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            original = root / 'original.bin'
            original.write_bytes(b'x' * 8192)
            os.link(original, root / 'alias.bin')
            sizes, files = diskhog.tree_sizes(directory)
            self.assertEqual(sizes[directory], original.stat().st_blocks * 512)
            self.assertEqual(len(files), 1)
