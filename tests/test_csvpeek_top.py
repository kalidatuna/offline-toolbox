import pathlib, subprocess, sys, tempfile, unittest

class TopTests(unittest.TestCase):
    def test_documented_top_option_controls_frequent_values(self):
        with tempfile.TemporaryDirectory() as directory:
            csv = pathlib.Path(directory) / 'fruit.csv'
            csv.write_text('fruit\napple\napple\nbanana\npeach\n')
            script = pathlib.Path(__file__).resolve().parents[1] / 'cli' / 'csvpeek.py'
            result = subprocess.run([sys.executable, str(script), str(csv), '--top', '1'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('apple(2)', result.stdout)
            self.assertNotIn('banana(1)', result.stdout)
            bad = subprocess.run([sys.executable, str(script), str(csv), '--top', '0'], capture_output=True, text=True)
            self.assertEqual(bad.returncode, 2)
