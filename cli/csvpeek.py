#!/usr/bin/env python3
"""csvpeek - instant health report for a CSV: types, nulls, uniques, ragged rows, dupes.

  csvpeek.py data.csv [--delimiter ';'] [--top 3]
"""
import argparse
import csv
import sys
from collections import Counter
from datetime import datetime

DATE_FMTS = ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S")


def kind(v):
    try:
        int(v)
        return "int"
    except ValueError:
        pass
    try:
        float(v)
        return "float"
    except ValueError:
        pass
    if v.lower() in ("true", "false", "yes", "no"):
        return "bool"
    for f in DATE_FMTS:
        try:
            datetime.strptime(v, f)
            return "date"
        except ValueError:
            pass
    return "text"


def analyze(rows, header):
    ncol = len(header)
    cols = [[] for _ in range(ncol)]
    ragged = []
    for i, r in enumerate(rows, start=2):
        if len(r) != ncol:
            ragged.append(i)
        for j in range(ncol):
            cols[j].append(r[j].strip() if j < len(r) else "")
    dupes = sum(c - 1 for c in Counter(map(tuple, rows)).values() if c > 1)
    stats = []
    for name, vals in zip(header, cols):
        filled = [v for v in vals if v != ""]
        kinds = Counter(kind(v) for v in filled)
        if set(kinds) == {"int", "float"}:
            kinds = Counter({"float": sum(kinds.values())})
        main = kinds.most_common(1)[0][0] if kinds else "empty"
        s = {"name": name, "type": main, "mixed": len(kinds) > 1, "nulls": len(vals) - len(filled),
             "unique": len(set(filled)), "top": Counter(filled).most_common(3)}
        if main in ("int", "float") and not s["mixed"]:
            nums = [float(v) for v in filled]
            s.update(min=min(nums), max=max(nums), mean=sum(nums) / len(nums))
        stats.append(s)
    return {"rows": len(rows), "cols": ncol, "ragged": ragged, "dupes": dupes, "stats": stats}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--delimiter", default=None)
    a = ap.parse_args(argv)
    with open(a.file, newline="", encoding="utf-8-sig") as f:
        sample = f.read(4096)
        f.seek(0)
        delim = a.delimiter
        if not delim:
            try:
                delim = csv.Sniffer().sniff(sample, ",;\t|").delimiter
            except csv.Error:
                delim = ","
        data = list(csv.reader(f, delimiter=delim))
    if not data:
        print("empty file")
        return 1
    res = analyze(data[1:], data[0])
    print(f"{res['rows']} rows x {res['cols']} cols | duplicate rows: {res['dupes']} | ragged rows: {len(res['ragged'])}")
    if res["ragged"]:
        print(f"  ragged at lines: {res['ragged'][:10]}{'...' if len(res['ragged']) > 10 else ''}")
    print(f"\n{'column':<20}{'type':<8}{'nulls':>6}{'unique':>8}  notes")
    for s in res["stats"]:
        note = ""
        if "min" in s:
            note = f"min={s['min']:g} max={s['max']:g} mean={s['mean']:.4g}"
        else:
            note = ", ".join(f"{v}({c})" for v, c in s["top"])[:50]
        if s["mixed"]:
            note = "MIXED TYPES; " + note
        print(f"{s['name'][:19]:<20}{s['type']:<8}{s['nulls']:>6}{s['unique']:>8}  {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
