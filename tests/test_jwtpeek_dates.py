import base64, json, os, pathlib, subprocess, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cli'))
import jwtpeek

class DateTests(unittest.TestCase):
    def test_expiry_boundary_and_zero_clock(self):
        self.assertTrue(any('EXPIRED' in warning for warning in jwtpeek.analyze({}, {'exp': 10}, now=10)))
        self.assertEqual(jwtpeek.analyze({}, {'exp': 1, 'nbf': 0}, now=0), [])

    def test_malformed_dates_return_cli_error_without_traceback(self):
        script = pathlib.Path(__file__).resolve().parents[1] / 'cli' / 'jwtpeek.py'
        encode = lambda value: base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip('=')
        for value in ('tomorrow', True, None, float('nan'), 10**100):
            with self.subTest(value=value):
                token = encode({'alg': 'HS256'}) + '.' + encode({'exp': value}) + '.'
                result = subprocess.run([sys.executable, str(script), token], capture_output=True, text=True)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertNotIn('Traceback', result.stderr)
                self.assertEqual(result.stdout, '')
