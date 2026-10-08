import os, pathlib, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cli'))
import envdiff

class QuoteTests(unittest.TestCase):
    def test_comments_after_quoted_values_preserve_contents_and_empty_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / 'synthetic.env'
            path.write_text("A='hello # inside' # outside\nB=\"\" # empty\nC=plain # comment\n")
            self.assertEqual(envdiff.parse(path), {'A': 'hello # inside', 'B': '', 'C': 'plain'})
