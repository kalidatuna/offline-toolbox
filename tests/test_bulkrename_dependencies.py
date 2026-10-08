import contextlib, io, os, pathlib, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cli'))
import bulkrename

class RenameDependencyTests(unittest.TestCase):
    def test_apply_refuses_a_destination_that_is_another_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / 'a.txt').write_text('first')
            (root / 'aa.txt').write_text('second')
            with contextlib.redirect_stdout(io.StringIO()):
                code = bulkrename.main([directory, '^a', 'aa', '--apply'])
            self.assertEqual(code, 2)
            self.assertEqual((root / 'a.txt').read_text(), 'first')
            self.assertEqual((root / 'aa.txt').read_text(), 'second')
            self.assertFalse((root / bulkrename.UNDO).exists())

    def test_broken_destination_symlinks_count_as_conflicts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / 'a.txt').write_text('first')
            (root / 'b.txt').symlink_to(root / 'missing.txt')
            self.assertEqual(bulkrename.check_conflicts([(str(root / 'a.txt'), str(root / 'b.txt'))]), {str(root / 'b.txt')})
