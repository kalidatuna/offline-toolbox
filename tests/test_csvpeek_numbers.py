import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cli'))
import csvpeek

class NumberTests(unittest.TestCase):
    def test_non_finite_values_are_reported_as_text(self):
        for value in ('NaN', 'inf', '-Infinity', '1e999'):
            with self.subTest(value=value):
                self.assertEqual(csvpeek.kind(value), 'text')
        stats = csvpeek.analyze([['1'], ['NaN']], ['value'])['stats'][0]
        self.assertTrue(stats['mixed'])
        self.assertNotIn('mean', stats)
