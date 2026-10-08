#!/usr/bin/env python3
"""tzmeet - find meeting times that fall inside everyone's working hours.

  tzmeet.py America/New_York Europe/London Asia/Kolkata
  tzmeet.py UTC Asia/Tokyo --date 2026-11-02 --hours 8-18 --step 30
Shows each slot in every zone; * marks slots good for all.
"""
import argparse
import sys
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def slots(zones, day, start_h=9, end_h=17, step=60):
    """Return list of (utc_dt, [local_dt...], ok_for_all) across the UTC day (+/-1 for wrap)."""
    if not zones:
        raise ValueError("at least one time zone is required")
    if isinstance(step, bool) or not isinstance(step, int) or step < 1:
        raise ValueError("step must be a positive integer")
    if (any(isinstance(hour, bool) or not isinstance(hour, int) for hour in (start_h, end_h))
            or not 0 <= start_h < end_h <= 24):
        raise ValueError("working hours must satisfy 0 <= start < end <= 24")
    zs = [ZoneInfo(z) for z in zones]
    base = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    out = []
    for m in range(0, 24 * 60, step):
        t = base + timedelta(minutes=m)
        locs = [t.astimezone(z) for z in zs]
        ok = all(start_h * 60 <= l.hour * 60 + l.minute < end_h * 60 for l in locs)
        out.append((t, locs, ok))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("zones", nargs="+")
    ap.add_argument("--date", default=None)
    ap.add_argument("--hours", default="9-17", help="working hours, e.g. 9-17")
    ap.add_argument("--step", type=int, default=60)
    ap.add_argument("--all", action="store_true", help="show every slot, not just matches")
    a = ap.parse_args(argv)
    try:
        lo, hi = (int(x) for x in a.hours.split("-"))
        day = date.fromisoformat(a.date) if a.date else date.today()
        rows = slots(a.zones, day, lo, hi, a.step)
    except (ValueError, ZoneInfoNotFoundError) as e:
        print("error:", e, file=sys.stderr)
        return 2
    print("  ".join(f"{z:<22}" for z in a.zones))
    good = 0
    for _, locs, ok in rows:
        good += ok
        if ok or a.all:
            print("  ".join(f"{l.strftime('%a %H:%M'):<22}" for l in locs) + ("  *" if ok else ""))
    if not good:
        print("no overlap in these working hours; widen --hours or pick the least-bad slot with --all")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
