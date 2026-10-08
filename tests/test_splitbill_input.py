import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cli'))
import splitbill

class ExpenseInputTests(unittest.TestCase):
    def test_invalid_amounts_and_shares_are_rejected(self):
        for line in ('alice', 'alice NaN', 'alice Infinity', 'alice -1', 'alice 0.001', 'alice 1 --', 'alice 1 -- bob,bob'):
            with self.subTest(line=line), self.assertRaises(ValueError):
                splitbill.parse([line])
        self.assertEqual(splitbill.parse(['alice 0.10 -- alice,bob'])[0][0][1].as_tuple().exponent, -2)
