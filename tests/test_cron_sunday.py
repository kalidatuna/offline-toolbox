import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cli'))
import cronexplain

class SundayTests(unittest.TestCase):
    def test_sunday_seven_works_at_the_end_of_weekday_ranges(self):
        self.assertEqual(cronexplain.parse_field('5-7', 4), {5, 6, 0})
        self.assertEqual(cronexplain.parse_field('0-7', 4), set(range(7)))
        self.assertEqual(cronexplain.parse_field('7', 4), {0})
