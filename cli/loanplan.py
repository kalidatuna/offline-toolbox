#!/usr/bin/env python3
"""loanplan - loan/mortgage payment, total interest, and savings from extra payments.

  loanplan.py 300000 6.5 30                    $300k at 6.5% for 30 years
  loanplan.py 300000 6.5 30 --extra 200        pay $200/month extra
  loanplan.py 300000 6.5 30 --schedule yearly  year-by-year balance table
"""
import argparse
import sys


def payment(principal, apr, years):
    n = int(years * 12)
    r = apr / 100 / 12
    return principal / n if r == 0 else principal * r / (1 - (1 + r) ** -n)


def simulate(principal, apr, years, extra=0.0):
    """Return (months, total_interest, yearly_rows)."""
    r = apr / 100 / 12
    pmt = payment(principal, apr, years) + extra
    bal, total_int, month, rows = principal, 0.0, 0, []
    yr_int = yr_prin = 0.0
    while bal > 0.005 and month < years * 12 + 1:
        month += 1
        interest = bal * r
        prin = min(pmt - interest, bal)
        bal -= prin
        total_int += interest
        yr_int += interest
        yr_prin += prin
        if month % 12 == 0 or bal <= 0.005:
            rows.append((month / 12, yr_prin, yr_int, max(bal, 0)))
            yr_int = yr_prin = 0.0
    return month, total_int, rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("principal", type=float)
    ap.add_argument("apr", type=float, help="annual rate in percent")
    ap.add_argument("years", type=float)
    ap.add_argument("--extra", type=float, default=0.0, help="extra monthly payment")
    ap.add_argument("--schedule", choices=["yearly"])
    a = ap.parse_args(argv)
    if a.principal <= 0 or a.years <= 0 or a.apr < 0:
        print("error: principal and years must be > 0, apr >= 0", file=sys.stderr)
        return 2
    pmt = payment(a.principal, a.apr, a.years)
    m0, i0, rows0 = simulate(a.principal, a.apr, a.years)
    print(f"Monthly payment: {pmt:,.2f}")
    print(f"Total interest:  {i0:,.2f}   (total paid {a.principal + i0:,.2f})")
    rows = rows0
    if a.extra:
        m1, i1, rows = simulate(a.principal, a.apr, a.years, a.extra)
        print(f"\nWith +{a.extra:,.2f}/mo: paid off in {m1 // 12}y {m1 % 12}m (saves {m0 - m1} months)")
        print(f"Interest saved:  {i0 - i1:,.2f}   (new interest {i1:,.2f})")
    if a.schedule:
        print(f"\n{'year':>5}{'principal':>14}{'interest':>14}{'balance':>16}")
        for y, p, i, b in rows:
            print(f"{y:>5.1f}{p:>14,.2f}{i:>14,.2f}{b:>16,.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
