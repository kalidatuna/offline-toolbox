#!/usr/bin/env python3
"""diskhog - where did my disk go? Biggest subdirectories and files, with bars.

  diskhog.py [DIR] [--depth 1] [--top 15] [--files]
"""
import argparse
import os
import sys


def human(n):
    for u in ("B", "K", "M", "G", "T"):
        if n < 1024 or u == "T":
            return f"{n:.0f}{u}" if u == "B" else f"{n:.1f}{u}"
        n /= 1024


def tree_sizes(root):
    """Return {dir: total bytes recursively} and list of (size, path) files."""
    sizes, files = {}, []
    for dp, dn, fn in os.walk(root, topdown=False):
        total = 0
        for f in fn:
            p = os.path.join(dp, f)
            try:
                if os.path.islink(p):
                    continue
                s = os.lstat(p).st_blocks * 512
            except OSError:
                continue
            total += s
            files.append((s, p))
        for d in dn:
            total += sizes.get(os.path.join(dp, d), 0)
        sizes[dp] = total
    return sizes, files


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir", nargs="?", default=".")
    ap.add_argument("--depth", type=int, default=1)
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--files", action="store_true", help="list biggest files instead")
    a = ap.parse_args(argv)
    root = os.path.abspath(a.dir)
    sizes, files = tree_sizes(root)
    total = sizes.get(root, 0) or 1
    if a.files:
        rows = sorted(files, reverse=True)[:a.top]
    else:
        rows = sorted(((s, d) for d, s in sizes.items()
                       if d != root and d[len(root):].count(os.sep) <= a.depth), reverse=True)[:a.top]
    print(f"{root}: {human(total)} total\n")
    for s, p in rows:
        bar = "#" * max(1, int(30 * s / total)) if s else ""
        print(f"{human(s):>8} {100 * s / total:5.1f}%  {bar:<30} {os.path.relpath(p, root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
