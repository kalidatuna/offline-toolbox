#!/usr/bin/env python3
"""pwcheck - offline password strength check + secure generator. Nothing leaves your machine.

  pwcheck.py check            (prompts silently)
  pwcheck.py gen [--length 20] [--words 5]      random password, or passphrase from --wordfile
"""
import argparse
import getpass
import math
import re
import secrets
import string
import sys

COMMON = {"password", "123456", "12345678", "qwerty", "abc123", "letmein", "monkey", "dragon", "111111",
          "iloveyou", "admin", "welcome", "login", "princess", "football", "master", "sunshine", "passw0rd"}
SEQS = ["abcdefghijklmnopqrstuvwxyz", "qwertyuiop", "asdfghjkl", "zxcvbnm", "0123456789"]


def pool_size(pw):
    size = 0
    for rx, n in ((r"[a-z]", 26), (r"[A-Z]", 26), (r"\d", 10), (r"[^A-Za-z0-9]", 32)):
        if re.search(rx, pw):
            size += n
    return size


def has_sequence(pw, n=4):
    low = pw.lower()
    for s in SEQS:
        for i in range(len(s) - n + 1):
            if s[i:i + n] in low or s[i:i + n][::-1] in low:
                return True
    return False


def assess(pw):
    bits = len(pw) * math.log2(pool_size(pw)) if pw else 0
    issues = []
    if pw.lower() in COMMON or re.sub(r"\d+$", "", pw.lower()) in COMMON:
        issues.append("is (or is based on) a very common password")
        bits = min(bits, 15)
    if re.search(r"(.)\1{2,}", pw):
        issues.append("has repeated characters")
        bits *= 0.8
    if has_sequence(pw):
        issues.append("contains a keyboard/alphabet/number sequence")
        bits *= 0.8
    if len(pw) < 12:
        issues.append("shorter than 12 characters")
    if len(set(pw)) <= len(pw) // 2:
        issues.append("low character variety")
        bits *= 0.85
    label = ("very weak", "weak", "fair", "strong", "very strong")[min(4, int(bits // 20))] if bits < 100 else "very strong"
    return {"bits": round(bits, 1), "label": label, "issues": issues}


def generate(length=20, words=0, wordlist=None):
    if words:
        if not wordlist:
            raise ValueError("--wordfile required for passphrases")
        return "-".join(secrets.choice(wordlist) for _ in range(words))
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*-_=+?"
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in pw) and any(c.isupper() for c in pw)
                and any(c.isdigit() for c in pw) and any(c in "!@#$%^&*-_=+?" for c in pw)):
            return pw


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    g = sub.add_parser("gen")
    g.add_argument("--length", type=int, default=20)
    g.add_argument("--words", type=int, default=0)
    g.add_argument("--wordfile")
    a = ap.parse_args(argv)
    if a.cmd == "check":
        r = assess(getpass.getpass("password: "))
        print(f"{r['label']} (~{r['bits']} bits)")
        for i in r["issues"]:
            print(" -", i)
        return 0
    wl = open(a.wordfile).read().split() if a.wordfile else None
    try:
        print(generate(a.length, a.words, wl))
    except ValueError as e:
        print("error:", e, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
