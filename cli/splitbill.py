#!/usr/bin/env python3
"""splitbill - split shared expenses; outputs the fewest payments to settle up.

Input lines (file or stdin):   payer amount [description] [-- shared,with,names]
  alice 90 dinner
  bob 30 taxi -- alice,bob
  carol 12.50 coffee -- carol,bob
Without '--' the expense is split among everyone who appears in the file.
  splitbill.py trip.txt
"""
import argparse
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CENT = Decimal("0.01")


def parse(lines):
    expenses, people = [], []
    for number, raw in enumerate(lines, 1):
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        main, separator, share = raw.partition("--")
        toks = main.split()
        if len(toks) < 2:
            raise ValueError(f"line {number}: expected payer and amount")
        payer = toks[0]
        try:
            amount = Decimal(toks[1])
            if not amount.is_finite() or amount < 0 or amount != amount.quantize(CENT):
                raise ValueError(f"line {number}: amount must be nonnegative and use whole cents")
        except InvalidOperation as error:
            raise ValueError(f"line {number}: invalid decimal amount") from error
        who = [w.strip() for w in share.split(",") if w.strip()] if separator else None
        if separator and (not who or len(set(who)) != len(who)):
            raise ValueError(f"line {number}: specify a nonempty list of unique participants")
        expenses.append((payer, amount, who))
        for n in [payer] + (who or []):
            if n not in people:
                people.append(n)
    return expenses, people


def balances(expenses, people):
    bal = {p: Decimal(0) for p in people}
    for payer, amt, who in expenses:
        who = who or people
        share = (amt / len(who)).quantize(CENT, ROUND_HALF_UP)
        bal[payer] += amt
        for w in who:
            bal[w] -= share
        # put rounding remainder on the payer so totals stay exact
        bal[payer] -= amt - share * len(who)
    return bal


def settle(bal):
    owe = sorted(((-b, p) for p, b in bal.items() if b < 0), reverse=True)  # debtors
    get = sorted(((b, p) for p, b in bal.items() if b > 0), reverse=True)   # creditors
    owe, get = [list(x) for x in owe], [list(x) for x in get]
    pays = []
    while owe and get:
        d, c = owe[0], get[0]
        amt = min(d[0], c[0])
        if amt >= CENT:
            pays.append((d[1], c[1], amt))
        d[0] -= amt
        c[0] -= amt
        if d[0] < CENT:
            owe.pop(0)
        if c[0] < CENT:
            get.pop(0)
        owe.sort(reverse=True)
        get.sort(reverse=True)
    return pays


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?", default="-")
    a = ap.parse_args(argv)
    src = sys.stdin if a.file == "-" else open(a.file)
    try:
        expenses, people = parse(src)
    except Exception as e:
        print("error: bad input:", e, file=sys.stderr)
        return 2
    bal = balances(expenses, people)
    print("Net balance (+ is owed money):")
    for p, b in bal.items():
        print(f"  {p:<12}{b:>10.2f}")
    print("\nSettle up:")
    pays = settle(bal)
    for d, c, amt in pays:
        print(f"  {d} pays {c} {amt:.2f}")
    if not pays:
        print("  all even")
    return 0


if __name__ == "__main__":
    sys.exit(main())
