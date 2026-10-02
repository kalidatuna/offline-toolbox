#!/usr/bin/env python3
"""gittidy - list local branches that are merged or stale; delete them safely on request.

  gittidy.py [--base main] [--stale-days 60]       report
  gittidy.py --delete-merged                       `git branch -d` merged ones (safe; refuses unmerged)
"""
import argparse
import subprocess
import sys
import time


def git(*args):
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip() or "git failed")
    return r.stdout


def default_base():
    for b in ("main", "master"):
        if subprocess.run(["git", "rev-parse", "--verify", "-q", b], capture_output=True).returncode == 0:
            return b
    raise RuntimeError("no main/master branch; pass --base")


def branches(base, stale_days, now=None):
    now = now or time.time()
    current = git("rev-parse", "--abbrev-ref", "HEAD").strip()
    merged = {b.strip("* ").strip() for b in git("branch", "--merged", base).splitlines()}
    out = []
    for line in git("for-each-ref", "--format=%(refname:short)|%(committerdate:unix)|%(subject)", "refs/heads").splitlines():
        name, ts, subj = line.split("|", 2)
        if name in (base, current):
            continue
        age = int((now - int(ts)) / 86400)
        out.append({"name": name, "age": age, "merged": name in merged, "stale": age >= stale_days, "subject": subj})
    return sorted(out, key=lambda b: -b["age"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base")
    ap.add_argument("--stale-days", type=int, default=60)
    ap.add_argument("--delete-merged", action="store_true")
    a = ap.parse_args(argv)
    try:
        base = a.base or default_base()
        bs = branches(base, a.stale_days)
    except RuntimeError as e:
        print("error:", e, file=sys.stderr)
        return 2
    for b in bs:
        tag = "MERGED" if b["merged"] else "STALE " if b["stale"] else "active"
        print(f"{tag}  {b['age']:>4}d  {b['name']:<30} {b['subject'][:50]}")
    if a.delete_merged:
        for b in bs:
            if b["merged"]:
                print(git("branch", "-d", b["name"]).strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
