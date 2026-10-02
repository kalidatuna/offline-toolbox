#!/usr/bin/env python3
"""dupefind - find duplicate files by content. Report only by default.

  dupefind.py DIR [DIR...]            list duplicate groups + wasted space
  dupefind.py DIR --move-to TRASH     keep oldest of each group, move rest to TRASH
  dupefind.py DIR --min-size 1M       ignore small files
"""
import argparse
import hashlib
import os
import shutil
import sys
from collections import defaultdict


def parse_size(s):
    units = {"k": 1024, "m": 1024**2, "g": 1024**3}
    s = s.strip().lower()
    return int(float(s[:-1]) * units[s[-1]]) if s[-1] in units else int(s)


def human(n):
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or u == "TB":
            return f"{n:.1f}{u}" if u != "B" else f"{n}B"
        n /= 1024


def file_hash(path, limit=None):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        data = f.read(limit) if limit else None
        if data is not None:
            h.update(data)
        else:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    return h.hexdigest()


def find_dupes(roots, min_size=1):
    by_size = defaultdict(list)
    seen = set()
    for root in roots:
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if not d.startswith(".git")]
            for name in fn:
                p = os.path.join(dp, name)
                try:
                    st = os.lstat(p)
                except OSError:
                    continue
                if not os.path.isfile(p) or os.path.islink(p) or st.st_size < min_size:
                    continue
                if (st.st_dev, st.st_ino) in seen:  # hardlink to same data
                    continue
                seen.add((st.st_dev, st.st_ino))
                by_size[st.st_size].append(p)
    groups = []
    for size, paths in by_size.items():
        if len(paths) < 2:
            continue
        # cheap prefix hash first, full hash only on collisions
        by_prefix = defaultdict(list)
        for p in paths:
            try:
                by_prefix[file_hash(p, 4096)].append(p)
            except OSError:
                pass
        for cand in by_prefix.values():
            if len(cand) < 2:
                continue
            full = defaultdict(list)
            for p in cand:
                try:
                    full[file_hash(p)].append(p)
                except OSError:
                    pass
            groups += [(size, sorted(v, key=os.path.getmtime)) for v in full.values() if len(v) > 1]
    return sorted(groups, key=lambda g: -g[0] * (len(g[1]) - 1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--min-size", default="1", help="e.g. 100k, 5M")
    ap.add_argument("--move-to", help="move duplicates (all but oldest) here")
    a = ap.parse_args(argv)
    groups = find_dupes(a.dirs, parse_size(a.min_size))
    wasted = 0
    for size, paths in groups:
        wasted += size * (len(paths) - 1)
        print(f"\n{human(size)} x{len(paths)}")
        for i, p in enumerate(paths):
            print(f"  {'KEEP' if i == 0 else 'dupe'}  {p}")
    print(f"\n{len(groups)} duplicate groups, {human(wasted)} reclaimable")
    if a.move_to and groups:
        os.makedirs(a.move_to, exist_ok=True)
        for _, paths in groups:
            for p in paths[1:]:
                dest = os.path.join(a.move_to, os.path.basename(p))
                n = 1
                while os.path.exists(dest):
                    dest = os.path.join(a.move_to, f"{n}_{os.path.basename(p)}")
                    n += 1
                shutil.move(p, dest)
        print(f"moved duplicates to {a.move_to}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
