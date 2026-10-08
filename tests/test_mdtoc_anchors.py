import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cli'))
import mdtoc

class AnchorTests(unittest.TestCase):
    def test_duplicate_suffixes_do_not_collide_with_literal_headings(self):
        headings = mdtoc.headings('## foo\n## foo-1\n## foo\n## foo-1\n')
        self.assertEqual([anchor for _, _, anchor in headings], ['foo', 'foo-1', 'foo-2', 'foo-1-1'])
