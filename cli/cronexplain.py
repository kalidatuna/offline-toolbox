#!/usr/bin/env python3
"""cronexplain - translate a 5-field cron expression to English and list next runs.

  cronexplain.py '*/15 9-17 * * 1-5' [--next 5] [--from 2026-01-01T00:00]
Supports * , - / lists, month/day names, @daily-style aliases.
"""
import argparse
import sys
from datetime import datetime, timedelta

ALIASES = {"@yearly": "0 0 1 1 *", "@annually": "0 0 1 1 *", "@monthly": "0 0 1 * *",
           "@weekly": "0 0 * * 0", "@daily": "0 0 * * *", "@midnight": "0 0 * * *", "@hourly": "0 * * * *"}
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
DAYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]
MONTH_FULL = ["January", "February", "March", "April", "May", "June", "July", "August",
              "September", "October", "November", "December"]
DAY_FULL = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
RANGES = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 6)]


def parse_field(f, idx):
    lo, hi = RANGES[idx]
    if idx == 4:
        hi = 7
    names = MONTHS if idx == 3 else DAYS if idx == 4 else None

    def val(tok):
        t = tok.lower()
        if names and t in names:
            return names.index(t) + (1 if idx == 3 else 0)
        n = int(tok)
        return n

    out = set()
    for part in f.split(","):
        rng, _, step = part.partition("/")
        step = int(step) if step else 1
        if step < 1:
            raise ValueError(f"bad step in '{part}'")
        if rng == "*":
            a, b = lo, hi
        elif "-" in rng:
            x, y = rng.split("-")
            a, b = val(x), val(y)
        else:
            a = val(rng)
            b = hi if step != 1 or "/" in part else a
        if a < lo or b > hi or a > b:
            raise ValueError(f"value out of range in '{part}' (allowed {lo}-{hi})")
        out.update(value % 7 if idx == 4 else value for value in range(a, b + 1, step))
    return out


def parse(expr):
    expr = ALIASES.get(expr.strip(), expr)
    fields = expr.split()
    if len(fields) != 5:
        raise ValueError("need 5 fields: minute hour day-of-month month day-of-week")
    return [parse_field(f, i) for i, f in enumerate(fields)], fields


def compress(vals, full, offset=0):
    vals = sorted(vals)
    name = (lambda v: full[v - offset]) if full else str
    runs, i = [], 0
    while i < len(vals):
        j = i
        while j + 1 < len(vals) and vals[j + 1] == vals[j] + 1:
            j += 1
        if j - i >= 2:
            runs.append(f"{name(vals[i])} through {name(vals[j])}")
        else:
            runs += [name(v) for v in vals[i:j + 1]]
        i = j + 1
    return ", ".join(runs)


def describe(expr):
    sets, raw = parse(expr)
    mi, ho, dom, mon, dow = sets
    parts = []
    if raw[0].startswith("*/") and raw[1] == "*":
        parts.append(f"Every {raw[0][2:]} minutes")
    elif raw[0] == "*" and raw[1] == "*":
        parts.append("Every minute")
    elif len(mi) == 1 and len(ho) == 1:
        parts.append(f"At {next(iter(ho)):02d}:{next(iter(mi)):02d}")
    else:
        parts.append(f"At minute {compress(mi, None)}" + ("" if raw[1] == "*" else f" past hour {compress(ho, None)}"))
    if raw[2] != "*":
        parts.append(f"on day-of-month {compress(dom, None)}")
    if raw[4] != "*":
        parts.append(f"on {compress(dow, DAY_FULL)}")
    if raw[3] != "*":
        parts.append(f"in {compress(mon, MONTH_FULL, 1)}")
    note = " (day-of-month OR day-of-week matches)" if raw[2] != "*" and raw[4] != "*" else ""
    return " ".join(parts) + note


def next_runs(expr, start, n):
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("run count must be a positive integer")
    (mi, ho, dom, mon, dow), raw = parse(expr)
    t = start.replace(second=0, microsecond=0) + timedelta(minutes=1)
    out, limit = [], 366 * 24 * 60 * 5
    for _ in range(limit):
        if t.month in mon and t.hour in ho and t.minute in mi:
            d_ok, w_ok = t.day in dom, (t.isoweekday() % 7) in dow
            ok = (d_ok or w_ok) if raw[2] != "*" and raw[4] != "*" else (d_ok and w_ok)
            if ok:
                out.append(t)
                if len(out) == n:
                    break
        t += timedelta(minutes=1)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("expr")
    ap.add_argument("--next", type=int, default=5)
    ap.add_argument("--from", dest="start")
    a = ap.parse_args(argv)
    try:
        print(describe(a.expr))
        start = datetime.fromisoformat(a.start) if a.start else datetime.now()
        for t in next_runs(a.expr, start, a.next):
            print("  next:", t.strftime("%a %Y-%m-%d %H:%M"))
    except ValueError as e:
        print("error:", e, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
