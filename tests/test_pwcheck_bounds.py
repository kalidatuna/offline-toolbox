import os, pathlib, subprocess, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cli'))
import pwcheck

class GeneratorTests(unittest.TestCase):
    def test_impossible_password_lengths_exit_instead_of_looping(self):
        script = pathlib.Path(__file__).resolve().parents[1] / 'cli' / 'pwcheck.py'
        for length in (-1, 0, 1, 3):
            with self.subTest(length=length):
                try:
                    result = subprocess.run([sys.executable, str(script), 'gen', '--length', str(length)], capture_output=True, text=True, timeout=1)
                except subprocess.TimeoutExpired:
                    self.fail('Impossible password length loops indefinitely')
                self.assertEqual(result.returncode, 2)
                self.assertIn('at least 4', result.stderr)

    def test_negative_passphrase_word_count_is_rejected(self):
        with self.assertRaises(ValueError):
            pwcheck.generate(words=-1, wordlist=['apple', 'banana'])
