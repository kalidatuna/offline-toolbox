import pathlib, subprocess, sys, tempfile, unittest

class SizeTests(unittest.TestCase):
    def test_invalid_minimum_sizes_return_cli_usage_errors(self):
        script = pathlib.Path(__file__).resolve().parents[1] / 'cli' / 'dupefind.py'
        with tempfile.TemporaryDirectory() as directory:
            for value in ('', '-1', '-0.0001K', 'NaN', 'infM', 'bad'):
                with self.subTest(value=value):
                    result = subprocess.run([sys.executable, str(script), directory, '--min-size=' + value], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertNotIn('Traceback', result.stderr)
                    self.assertEqual(result.stdout, '')
