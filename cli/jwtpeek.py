#!/usr/bin/env python3
"""jwtpeek - decode a JWT locally (no network, signature NOT verified) and flag problems.

  jwtpeek.py TOKEN        or:   echo TOKEN | jwtpeek.py -
Warns on: expired, not-yet-valid, alg=none, missing exp.
"""
import argparse
import base64
import json
import sys
import time
from datetime import datetime, timezone


def b64d(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def decode(token):
    token = token.strip()
    if token.lower().startswith("bearer "):
        token = token[7:]
    parts = token.split(".")
    if len(parts) not in (2, 3):
        raise ValueError("not a JWT (expected 3 dot-separated parts)")
    try:
        return json.loads(b64d(parts[0])), json.loads(b64d(parts[1]))
    except Exception as e:
        raise ValueError(f"cannot decode: {e}")


def analyze(header, payload, now=None):
    now = now or time.time()
    warns = []
    if str(header.get("alg", "")).lower() == "none":
        warns.append("alg=none: token is unsigned")
    exp, nbf = payload.get("exp"), payload.get("nbf")
    if exp is None:
        warns.append("no exp claim: token never expires")
    elif exp < now:
        warns.append(f"EXPIRED {int(now - exp)}s ago")
    if nbf and nbf > now:
        warns.append(f"not valid yet (nbf in {int(nbf - now)}s)")
    return warns


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("token")
    a = ap.parse_args(argv)
    tok = sys.stdin.read() if a.token == "-" else a.token
    try:
        header, payload = decode(tok)
    except ValueError as e:
        print("error:", e, file=sys.stderr)
        return 2
    print("HEADER ", json.dumps(header, indent=2))
    print("PAYLOAD", json.dumps(payload, indent=2))
    for k in ("iat", "nbf", "exp"):
        if isinstance(payload.get(k), (int, float)):
            print(f"{k}: {datetime.fromtimestamp(payload[k], timezone.utc).isoformat()}")
    warns = analyze(header, payload)
    for w in warns:
        print("WARN:", w)
    return 1 if warns else 0


if __name__ == "__main__":
    sys.exit(main())
