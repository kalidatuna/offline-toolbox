#!/usr/bin/env python3
"""secretscan - find leaked secrets (API keys, tokens, private keys) before you commit.

  secretscan.py [PATH...]   scan files (default .); secrets are masked in output
Exit code 1 if anything found. Add `# secretscan:ignore` on a line to skip it.
"""
import argparse
import math
import os
import re
import sys

PATTERNS = {
    "AWS access key": r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b",
    "GitHub token": r"\bgh[pousr]_[A-Za-z0-9]{36,}\b",
    "Slack token": r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b",
    "Stripe live key": r"\b[sr]k_live_[0-9a-zA-Z]{20,}\b",
    "Google API key": r"\bAIza[0-9A-Za-z_\-]{35}\b",
    "Anthropic/OpenAI key": r"\bsk-(?:ant-)?[A-Za-z0-9_\-]{32,}\b",
    "Private key block": r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----",
    "JWT": r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b",
    "Credentials in URL": r"[a-z][a-z0-9+.-]*://[^\s:/@]+:[^\s:/@]{3,}@[^\s/]+",
    "Generic secret assignment": r"""(?i)\b(?:api[_-]?key|secret|passwd|password|token|auth)\w*\s*[:=]\s*['"]([A-Za-z0-9/+_\-=]{12,})['"]""",
}
COMPILED = {k: re.compile(v) for k, v in PATTERNS.items()}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next"}
SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".gz", ".ico", ".woff", ".woff2", ".lock", ".so", ".pyc"}


def entropy(s):
    if not s:
        return 0.0
    return -sum((s.count(c) / len(s)) * math.log2(s.count(c) / len(s)) for c in set(s))


def mask(s):
    return s if len(s) <= 8 else s[:4] + "*" * min(len(s) - 8, 12) + s[-4:]


def scan_text(text):
    hits = []
    for n, line in enumerate(text.splitlines(), 1):
        if "secretscan:ignore" in line:
            continue
        for name, rx in COMPILED.items():
            m = rx.search(line)
            if not m:
                continue
            val = m.group(1) if m.groups() else m.group(0)
            if name == "Generic secret assignment" and (entropy(val) < 3.0 or val.lower().startswith(("your", "example", "changeme"))):
                continue
            hits.append((n, name, mask(val)))
            break
    return hits


def walk_files(root):
    if os.path.isfile(root):
        yield root
        return
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            yield os.path.join(dp, f)


def scan_path(root):
    for p in walk_files(root):
        if os.path.splitext(p)[1].lower() in SKIP_EXT:
            continue
        try:
            if os.path.getsize(p) > 2_000_000:
                continue
            with open(p, encoding="utf-8") as f:
                text = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        for h in scan_text(text):
            yield (p,) + h


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", default=["."])
    a = ap.parse_args(argv)
    n = 0
    for root in a.paths:
        for path, line, kind, masked in scan_path(root):
            print(f"{path}:{line}: {kind}: {masked}")
            n += 1
    print(f"{n} potential secret(s) found" if n else "clean")
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main())
