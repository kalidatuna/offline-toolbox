import os, sys, unittest
from decimal import Decimal
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cli'))
import splitbill

class RoundingTests(unittest.TestCase):
    def test_payer_not_in_shared_group_receives_the_full_amount(self):
        expenses, people = splitbill.parse(['alice 1.00 -- bob,carol,dan'])
        result = splitbill.balances(expenses, people)
        self.assertEqual(result, {'alice': Decimal('1.00'), 'bob': Decimal('-0.34'), 'carol': Decimal('-0.33'), 'dan': Decimal('-0.33')})
        self.assertEqual(sum(result.values()), Decimal(0))

    def test_a_single_cent_is_charged_to_a_beneficiary(self):
        expenses, people = splitbill.parse(['alice 0.01 -- bob,carol,dan'])
        result = splitbill.balances(expenses, people)
        self.assertEqual(result['alice'], Decimal('0.01'))
        self.assertEqual(result['bob'], Decimal('-0.01'))
        self.assertEqual(sum(result.values()), Decimal(0))
