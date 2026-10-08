#!/usr/bin/env python3
"""jwtpeek - decode a JWT locally (no network, signature NOT verified) and flag problems.

  jwtpeek.py TOKEN        or:   echo TOKEN | jwtpeek.py -
Warns on: expired, not-yet-valid, alg=none, missing exp.
"""
import argparse
import base64
import json
import math
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
        header, payload = json.loads(b64d(parts[0])), json.loads(b64d(parts[1]))
    except Exception as e:
        raise ValueError(f"cannot decode: {e}") from e
    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise ValueError("JWT header and payload must be JSON objects")
    return header, payload


def analyze(header, payload, now=None):
    now = time.time() if now is None else now
    for claim in ("iat", "nbf", "exp"):
        if claim in payload:
            value = payload[claim]
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or (isinstance(value, float) and not math.isfinite(value))):
                raise ValueError(f"{claim} must be a finite numeric date")
    warns = []
    if str(header.get("alg", "")).lower() == "none":
        warns.append("alg=none: token is unsigned")
    exp, nbf = payload.get("exp"), payload.get("nbf")
    if exp is None:
        warns.append("no exp claim: expiration is unspecified")
    elif exp <= now:
        warns.append(f"EXPIRED {int(now - exp)}s ago")
    if nbf is not None and nbf > now:
        warns.append(f"not valid yet (nbf in {int(nbf - now)}s)")
    return warns


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("token")
    a = ap.parse_args(argv)
    tok = sys.stdin.read() if a.token == "-" else a.token
    try:
        header, payload = decode(tok)
        warns = analyze(header, payload)
        dates = [(key, datetime.fromtimestamp(payload[key], timezone.utc).isoformat())
                 for key in ("iat", "nbf", "exp") if key in payload]
    except (ValueError, OverflowError, OSError) as e:
        print("error:", e, file=sys.stderr)
        return 2
    print("HEADER ", json.dumps(header, indent=2))
    print("PAYLOAD", json.dumps(payload, indent=2))
    for key, date in dates:
        print(f"{key}: {date}")
    for w in warns:
        print("WARN:", w)
    return 1 if warns else 0


if __name__ == "__main__":
    sys.exit(main())
