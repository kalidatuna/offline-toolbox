#!/usr/bin/env python3
"""logsift - collapse a huge log into its distinct problems.

Normalises numbers, UUIDs, hex, IPs, timestamps so repeated errors group together.
  logsift.py app.log [--level ERROR,WARN] [--top 15] [--examples]
  cat app.log | logsift.py -
"""
import argparse
import re
import sys
from collections import Counter, defaultdict

SUBS = [
    (re.compile(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?\b"), "<TS>"),
    (re.compile(r"\b[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\b"), "<UUID>"),
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?\b"), "<IP>"),
    (re.compile(r"\b0x[0-9a-fA-F]+\b"), "<HEX>"),
    (re.compile(r"\b[0-9a-f]{16,}\b"), "<HASH>"),
    (re.compile(r"(?<!\w)\d+(?:\.\d+)?"), "<N>"),
]
LEVELS = ("FATAL", "CRITICAL", "ERROR", "WARN", "WARNING", "INFO", "DEBUG", "TRACE")
LEVEL_RX = re.compile(r"\b(" + "|".join(LEVELS) + r")\b", re.I)


def normalize(line):
    for rx, rep in SUBS:
        line = rx.sub(rep, line)
    return re.sub(r"\s+", " ", line).strip()


def sift(lines, levels=None):
    counts, first, examples, levs = Counter(), {}, defaultdict(str), Counter()
    for n, line in enumerate(lines, 1):
        line = line.rstrip("\n")
        if not line.strip():
            continue
        m = LEVEL_RX.search(line)
        lv = m.group(1).upper() if m else "?"
        levs[lv] += 1
        if levels and lv not in levels:
            continue
        key = normalize(line)
        counts[key] += 1
        first.setdefault(key, n)
        examples.setdefault(key, line)
    return counts, first, examples, levs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="log file or - for stdin")
    ap.add_argument("--level", help="comma list, e.g. ERROR,WARN")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--examples", action="store_true", help="show first raw line of each group")
    a = ap.parse_args(argv)
    src = sys.stdin if a.file == "-" else open(a.file, errors="replace")
    levels = {l.strip().upper() for l in a.level.split(",")} if a.level else None
    if levels and "WARN" in levels:
        levels.add("WARNING")
    counts, first, ex, levs = sift(src, levels)
    print("levels: " + ", ".join(f"{k}={v}" for k, v in levs.most_common()))
    print(f"{sum(counts.values())} lines -> {len(counts)} distinct patterns\n")
    for key, c in counts.most_common(a.top):
        print(f"{c:>7}x  (first @ line {first[key]})  {key[:140]}")
        if a.examples:
            print(f"          e.g. {ex[key][:200]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
