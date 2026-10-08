import os, sys, unittest
from datetime import date
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cli'))
import tzmeet

class BoundTests(unittest.TestCase):
    def test_invalid_intervals_and_steps_are_rejected(self):
        for start, end, step in ((9, 17, -1), (9, 17, 0), (-1, 17, 60), (9, 25, 60), (17, 9, 60), (9, 9, 60)):
            with self.subTest(start=start, end=end, step=step), self.assertRaises(ValueError):
                tzmeet.slots(['UTC'], date(2026, 1, 1), start, end, step)
        with self.assertRaises(ValueError):
            tzmeet.slots([], date(2026, 1, 1))
        self.assertEqual(len(tzmeet.slots(['UTC'], date(2026, 1, 1), 0, 24)), 24)
