import os, pathlib, subprocess, sys, unittest
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cli'))
import cronexplain

class CountTests(unittest.TestCase):
    def test_invalid_run_counts_fail_before_schedule_parsing(self):
        for count in (0, -1, True, 1.5):
            with self.subTest(count=count), self.assertRaisesRegex(ValueError, 'positive integer'):
                cronexplain.next_runs('invalid expression', datetime(2026, 1, 1), count)

    def test_zero_count_cli_does_not_search_five_years_of_runs(self):
        script = pathlib.Path(__file__).resolve().parents[1] / 'cli' / 'cronexplain.py'
        try:
            result = subprocess.run([sys.executable, str(script), '* * * * *', '--next', '0'],
                                    capture_output=True, text=True, timeout=2)
        except subprocess.TimeoutExpired:
            self.fail('Zero run count must fail immediately instead of scanning years of schedules')
        self.assertEqual(result.returncode, 2)
