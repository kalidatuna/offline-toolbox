#!/usr/bin/env python3
"""sitecheck - batch uptime + TLS-expiry + redirect check for a list of URLs.

  sitecheck.py https://example.com https://api.example.org/health
  sitecheck.py -f urls.txt --warn-days 21 --timeout 8
Exit 1 if any site is down, slow-failing, or its cert expires within --warn-days. Cron friendly.
"""
import argparse
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlparse


def cert_days_left(host, port=443, timeout=8):
    ctx = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=timeout) as s:
        with ctx.wrap_socket(s, server_hostname=host) as t:
            exp = ssl.cert_time_to_seconds(t.getpeercert()["notAfter"])
    return int((exp - time.time()) / 86400)


def check(url, timeout=8, warn_days=14):
    if "://" not in url:
        url = "https://" + url
    res = {"url": url, "status": None, "ms": None, "cert_days": None, "final": None, "problems": []}
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "sitecheck/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            res["status"], res["final"] = r.status, r.geturl()
    except urllib.error.HTTPError as e:
        res["status"] = e.code
        res["problems"].append(f"HTTP {e.code}")
    except Exception as e:
        res["problems"].append(f"unreachable: {getattr(e, 'reason', e)}")
    res["ms"] = int((time.time() - t0) * 1000)
    p = urlparse(url)
    if p.scheme == "https" and not res["problems"]:
        try:
            res["cert_days"] = cert_days_left(p.hostname, p.port or 443, timeout)
            if res["cert_days"] < warn_days:
                res["problems"].append(f"cert expires in {res['cert_days']}d")
        except Exception as e:
            res["problems"].append(f"TLS error: {e}")
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("urls", nargs="*")
    ap.add_argument("-f", "--file")
    ap.add_argument("--timeout", type=float, default=8)
    ap.add_argument("--warn-days", type=int, default=14)
    a = ap.parse_args(argv)
    urls = list(a.urls)
    if a.file:
        urls += [l.strip() for l in open(a.file) if l.strip() and not l.startswith("#")]
    if not urls:
        ap.error("give URLs or -f file")
    bad = 0
    for u in urls:
        r = check(u, a.timeout, a.warn_days)
        mark = "FAIL" if r["problems"] else "ok  "
        cert = f"cert {r['cert_days']}d" if r["cert_days"] is not None else ""
        moved = f"-> {r['final']}" if r["final"] and r["final"].rstrip("/") != r["url"].rstrip("/") else ""
        print(f"{mark} {r['status'] or '---'} {r['ms']:>5}ms {cert:<11} {r['url']} {moved} {'; '.join(r['problems'])}")
        bad += bool(r["problems"])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
