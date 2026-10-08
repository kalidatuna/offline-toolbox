#!/usr/bin/env python3
"""bulkrename - regex rename with dry-run by default and one-command undo.

  bulkrename.py DIR 'IMG_(\\d+)' 'photo_\\1'              preview
  bulkrename.py DIR 'IMG_(\\d+)' 'photo_\\1' --apply      do it (writes .bulkrename-undo.json)
  bulkrename.py DIR --undo                               revert last run
  options: --ext .jpg  --recursive  --number 3 (append zero-padded counter)  --lower  --spaces _
"""
import argparse
import json
import os
import re
import sys

UNDO = ".bulkrename-undo.json"


def plan(root, pattern, repl, ext=None, recursive=False, number=0, lower=False, spaces=None):
    rx = re.compile(pattern) if pattern else None
    files = []
    for dp, dn, fn in os.walk(root):
        files += [(dp, f) for f in sorted(fn) if f != UNDO]
        if not recursive:
            break
    out, i = [], 0
    for dp, f in files:
        stem, e = os.path.splitext(f)
        if ext and e.lower() != ext.lower():
            continue
        new = rx.sub(repl, stem) if rx else stem
        if spaces is not None:
            new = new.replace(" ", spaces)
        if lower:
            new = new.lower()
        if number:
            i += 1
            new += f"_{i:0{number}d}"
        new += e
        if new != f:
            out.append((os.path.join(dp, f), os.path.join(dp, new)))
    return out


def check_conflicts(moves):
    dests = [d for _, d in moves]
    dup = {d for d in dests if dests.count(d) > 1}
    clash = {d for d in dests if os.path.lexists(d)}
    return dup | clash


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir")
    ap.add_argument("pattern", nargs="?")
    ap.add_argument("repl", nargs="?", default="")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--undo", action="store_true")
    ap.add_argument("--ext")
    ap.add_argument("--recursive", action="store_true")
    ap.add_argument("--number", type=int, default=0)
    ap.add_argument("--lower", action="store_true")
    ap.add_argument("--spaces")
    a = ap.parse_args(argv)
    undo_path = os.path.join(a.dir, UNDO)
    if a.undo:
        with open(undo_path) as f:
            moves = json.load(f)
        for src, dst in reversed(moves):
            os.rename(dst, src)
        os.remove(undo_path)
        print(f"reverted {len(moves)} renames")
        return 0
    moves = plan(a.dir, a.pattern, a.repl, a.ext, a.recursive, a.number, a.lower, a.spaces)
    if not moves:
        print("nothing to rename")
        return 0
    bad = check_conflicts(moves)
    for s, d in moves:
        print(f"{'!! ' if d in bad else ''}{os.path.relpath(s, a.dir)}  ->  {os.path.relpath(d, a.dir)}")
    if bad:
        print(f"\nABORT: {len(bad)} name collision(s); adjust pattern or use --number")
        return 2
    if not a.apply:
        print(f"\n{len(moves)} renames (dry run; add --apply)")
        return 0
    for s, d in moves:
        os.rename(s, d)
    with open(undo_path, "w") as f:
        json.dump(moves, f)
    print(f"\nrenamed {len(moves)} files; undo with --undo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
