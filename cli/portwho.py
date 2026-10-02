#!/usr/bin/env python3
"""portwho - "what is using port 3000?" and optionally free it. Linux (uses ss).

  portwho.py            list all listening ports with process
  portwho.py 3000       show who holds 3000
  portwho.py 3000 --kill   SIGTERM the holder (--force for SIGKILL)
"""
import argparse
import os
import re
import signal
import subprocess
import sys


def listening():
    out = subprocess.run(["ss", "-H", "-ltnp"], capture_output=True, text=True).stdout
    rows = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        addr = parts[3]
        port = int(addr.rsplit(":", 1)[1])
        procs = re.findall(r'\("([^"]+)",pid=(\d+)', line)
        rows.append({"port": port, "addr": addr, "procs": [(n, int(p)) for n, p in procs]})
    return sorted(rows, key=lambda r: r["port"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("port", nargs="?", type=int)
    ap.add_argument("--kill", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    rows = [r for r in listening() if a.port in (None, r["port"])]
    if not rows:
        print("nothing listening" + (f" on {a.port}" if a.port else ""))
        return 1
    for r in rows:
        who = ", ".join(f"{n} (pid {p})" for n, p in r["procs"]) or "unknown (needs sudo to see)"
        print(f"{r['addr']:<24} {who}")
        if a.kill:
            for _, pid in r["procs"]:
                os.kill(pid, signal.SIGKILL if a.force else signal.SIGTERM)
                print(f"  sent {'SIGKILL' if a.force else 'SIGTERM'} to {pid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
