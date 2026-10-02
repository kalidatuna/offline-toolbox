#!/usr/bin/env python3
"""envdiff - compare .env files by key. Never prints values.

  envdiff.py .env.example .env        keys missing / extra / empty
  envdiff.py a.env b.env --values     also report keys whose values differ (still no values shown)
Exit code 1 if differences found (CI friendly).
"""
import argparse
import re
import sys

LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*(.*?)\s*$")


def parse(path):
    env = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.lstrip().startswith("#"):
                continue
            m = LINE.match(line)
            if m:
                v = m.group(2)
                if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                    v = v[1:-1]
                elif " #" in v:
                    v = v.split(" #", 1)[0].rstrip()
                env[m.group(1)] = v
    return env


def diff(a, b, compare_values=False):
    res = {
        "missing_in_b": sorted(set(a) - set(b)),
        "extra_in_b": sorted(set(b) - set(a)),
        "empty_in_b": sorted(k for k in set(a) & set(b) if b[k] == "" and a[k] != ""),
        "different": sorted(k for k in set(a) & set(b) if compare_values and a[k] != b[k]),
    }
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("a", help="reference file (e.g. .env.example)")
    ap.add_argument("b", help="file to check (e.g. .env)")
    ap.add_argument("--values", action="store_true")
    args = ap.parse_args(argv)
    r = diff(parse(args.a), parse(args.b), args.values)
    titles = {
        "missing_in_b": f"Missing in {args.b}",
        "extra_in_b": f"Only in {args.b}",
        "empty_in_b": f"Empty in {args.b} (set in {args.a})",
        "different": "Values differ",
    }
    bad = False
    for k, keys in r.items():
        if keys:
            bad = True
            print(f"{titles[k]}:")
            for key in keys:
                print(f"  - {key}")
    if not bad:
        print("OK: no differences")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
