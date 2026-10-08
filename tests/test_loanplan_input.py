import pathlib, subprocess, sys, unittest

class LoanInputTests(unittest.TestCase):
    def test_invalid_terms_and_extra_payments_return_errors(self):
        script = pathlib.Path(__file__).resolve().parents[1] / 'cli' / 'loanplan.py'
        for arguments in (['100', '0', '0.01'], ['nan', '5', '1'], ['100', 'inf', '1'], ['100', '5', 'nan'], ['100', '5', '1', '--extra', '-1'], ['100', '5', '1', '--extra', 'nan']):
            with self.subTest(arguments=arguments):
                result = subprocess.run([sys.executable, str(script), *arguments], capture_output=True, text=True, timeout=2)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertNotIn('Traceback', result.stderr)
                self.assertEqual(result.stdout, '')
