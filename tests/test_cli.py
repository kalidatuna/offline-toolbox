import base64
import contextlib
import http.server
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cli"))

import bulkrename, cronexplain, csvpeek, dupefind, envdiff, jwtpeek, logsift  # noqa: E402
import loanplan, mdtoc, pwcheck, secretscan, sitecheck, splitbill, tzmeet, gittidy  # noqa: E402
import diskhog, portwho  # noqa: E402


def write(d, name, content=""):
    p = os.path.join(d, name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        f.write(content)
    return p


def run(mod, *args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = mod.main(list(args))
    return code, out.getvalue()


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_dupefind(self):
        write(self.d, "a.txt", "hello world")
        write(self.d, "sub/b.txt", "hello world")
        write(self.d, "c.txt", "different!!!")
        groups = dupefind.find_dupes([self.d])
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0][1]), 2)
        code, out = run(dupefind, self.d, "--move-to", os.path.join(self.d, "..", "trash_" + os.path.basename(self.d)))
        self.assertIn("1 duplicate groups", out)
        self.assertEqual(len(dupefind.find_dupes([self.d])), 0)

    def test_envdiff(self):
        a = write(self.d, "a", "A=1\nB=2\n# c\nexport C='x'\n")
        b = write(self.d, "b", "A=1\nC=\nD=4\n")
        r = envdiff.diff(envdiff.parse(a), envdiff.parse(b))
        self.assertEqual(r["missing_in_b"], ["B"])
        self.assertEqual(r["extra_in_b"], ["D"])
        self.assertEqual(r["empty_in_b"], ["C"])
        self.assertEqual(run(envdiff, a, b)[0], 1)
        self.assertEqual(run(envdiff, a, a)[0], 0)

    def test_secretscan(self):
        p = write(self.d, "x.py", 'k = "AKIAIOSFODNN7EXAMPLE"\npassword = "hunter2hunter2Zq9"\nok = 1\n')
        hits = list(secretscan.scan_path(p))
        kinds = {h[2] for h in hits}
        self.assertIn("AWS access key", kinds)
        self.assertIn("Generic secret assignment", kinds)
        for h in hits:
            self.assertNotIn("AKIAIOSFODNN7EXAMPLE", h[3])  # masked
        write(self.d, "y.py", 'k = "AKIAIOSFODNN7EXAMPLE"  # secretscan:ignore\npassword = "changeme_example1"\n')
        self.assertEqual(list(secretscan.scan_path(os.path.join(self.d, "y.py"))), [])

    def test_csvpeek(self):
        p = write(self.d, "d.csv", "id,name,score\n1,a,3.5\n2,b,\n2,b,\n3,c\n4,d,x\n")
        with open(p, newline="") as f:
            import csv
            data = list(csv.reader(f))
        r = csvpeek.analyze(data[1:], data[0])
        self.assertEqual(r["rows"], 5)
        self.assertEqual(r["ragged"], [5])
        self.assertEqual(r["dupes"], 1)
        self.assertEqual(r["stats"][0]["type"], "int")
        self.assertTrue(r["stats"][2]["mixed"])
        self.assertEqual(run(csvpeek, p)[0], 0)

    def test_logsift(self):
        lines = ["2026-01-01 10:00:01 ERROR db timeout after 30s user=123\n",
                 "2026-01-01 10:00:09 ERROR db timeout after 45s user=999\n",
                 "2026-01-01 10:00:10 INFO started\n"]
        counts, _, _, levs = logsift.sift(lines, {"ERROR"})
        self.assertEqual(len(counts), 1)
        self.assertEqual(list(counts.values()), [2])
        self.assertEqual(levs["INFO"], 1)

    def test_bulkrename(self):
        for n in ("IMG_001.jpg", "IMG_002.jpg", "notes.txt"):
            write(self.d, n)
        code, out = run(bulkrename, self.d, r"IMG_(\d+)", r"photo_\1", "--apply")
        self.assertEqual(sorted(os.listdir(self.d)), [".bulkrename-undo.json", "notes.txt", "photo_001.jpg", "photo_002.jpg"])
        run(bulkrename, self.d, "--undo")
        self.assertEqual(sorted(os.listdir(self.d)), ["IMG_001.jpg", "IMG_002.jpg", "notes.txt"])
        # collision
        code, _ = run(bulkrename, self.d, r"IMG_\d+", "same")
        self.assertEqual(code, 2)

    def test_cronexplain(self):
        self.assertEqual(cronexplain.describe("*/15 * * * *"), "Every 15 minutes")
        self.assertIn("At 09:30", cronexplain.describe("30 9 * * 1-5"))
        self.assertIn("Monday through Friday", cronexplain.describe("30 9 * * 1-5"))
        runs = cronexplain.next_runs("30 9 * * 1-5", datetime(2026, 10, 2, 10, 0), 3)  # Friday
        self.assertEqual([r.strftime("%a %H:%M") for r in runs], ["Mon 09:30", "Tue 09:30", "Wed 09:30"])
        self.assertEqual(cronexplain.describe("@daily"), "At 00:00")
        with self.assertRaises(ValueError):
            cronexplain.parse("61 * * * *")
        with self.assertRaises(ValueError):
            cronexplain.parse("* * *")

    def test_jwtpeek(self):
        def enc(o):
            return base64.urlsafe_b64encode(json.dumps(o).encode()).decode().rstrip("=")
        tok = f"{enc({'alg': 'none'})}.{enc({'sub': 'x', 'exp': 1000})}."
        h, p = jwtpeek.decode("Bearer " + tok)
        w = jwtpeek.analyze(h, p, now=2000)
        self.assertTrue(any("alg=none" in x for x in w))
        self.assertTrue(any("EXPIRED" in x for x in w))
        with self.assertRaises(ValueError):
            jwtpeek.decode("abc")

    def test_diskhog(self):
        write(self.d, "big/a.bin", "x" * 100000)
        write(self.d, "small/b.txt", "y")
        sizes, files = diskhog.tree_sizes(self.d)
        self.assertGreater(sizes[os.path.join(self.d, "big")], sizes[os.path.join(self.d, "small")])
        self.assertIn("big", run(diskhog, self.d)[1])

    def test_mdtoc(self):
        md = "# T\n## One\ntext\n```\n## not\n```\n## One\n### Sub *x*\n"
        toc = mdtoc.build_toc(md)
        self.assertEqual(toc, "- [One](#one)\n- [One](#one-1)\n  - [Sub *x*](#sub-x)")
        out = mdtoc.inject(md, toc)
        self.assertEqual(mdtoc.inject(out, toc), out)  # idempotent
        p = write(self.d, "r.md", md)
        run(mdtoc, p, "--write")
        run(mdtoc, p, "--write")
        self.assertEqual(open(p).read().count("<!-- toc -->"), 1)

    def test_tzmeet(self):
        rows = tzmeet.slots(["America/New_York", "Europe/London"], datetime(2026, 11, 2).date(), 9, 17, 60)
        oks = [t.hour for t, _, ok in rows if ok]
        self.assertEqual(oks, [14, 15, 16])  # UTC hours; NY=UTC-5 (DST ended Nov 1), London=UTC+0
        self.assertEqual(run(tzmeet, "Nope/Zone")[0], 2)

    def test_pwcheck(self):
        self.assertIn("common", " ".join(pwcheck.assess("password1")["issues"]))
        weak = pwcheck.assess("abc123")["bits"]
        strong = pwcheck.assess(pwcheck.generate(24))["bits"]
        self.assertGreater(strong, weak + 60)
        pw = pwcheck.generate(16)
        self.assertEqual(len(pw), 16)

    def test_sitecheck(self):
        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(s):
                s.send_response(200 if s.path == "/ok" else 500)
                s.end_headers()
            def log_message(*a): pass
        srv = http.server.HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{srv.server_port}"
        self.assertEqual(sitecheck.check(base + "/ok")["problems"], [])
        self.assertEqual(sitecheck.check(base + "/bad")["problems"], ["HTTP 500"])
        self.assertTrue(sitecheck.check("http://127.0.0.1:1", timeout=1)["problems"][0].startswith("unreachable"))
        srv.shutdown()

    def test_splitbill(self):
        exp, people = splitbill.parse(["alice 90 dinner", "bob 30 taxi -- alice,bob", "carol 10 x -- carol,bob"])
        bal = splitbill.balances(exp, people)
        self.assertEqual(sum(bal.values()), Decimal(0))
        pays = splitbill.settle(bal)
        net = {p: Decimal(0) for p in people}
        for d, c, a in pays:
            net[d] += a
            net[c] -= a
        for p in people:
            self.assertEqual(net[p] + bal[p], Decimal(0))
        self.assertLessEqual(len(pays), len(people) - 1)

    def test_loanplan(self):
        self.assertAlmostEqual(loanplan.payment(300000, 6.5, 30), 1896.20, places=2)
        m0, i0, _ = loanplan.simulate(300000, 6.5, 30)
        m1, i1, _ = loanplan.simulate(300000, 6.5, 30, 200)
        self.assertEqual(m0, 360)
        self.assertLess(m1, m0)
        self.assertLess(i1, i0)
        self.assertAlmostEqual(loanplan.payment(1200, 0, 1), 100)

    def test_gittidy(self):
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        g = lambda *a: subprocess.run(["git", *a], cwd=self.d, env=env, check=True, capture_output=True)
        g("init", "-q", "-b", "main")
        write(self.d, "f", "1")
        g("add", "."); g("commit", "-qm", "init")
        g("branch", "merged-one")
        g("checkout", "-qb", "wip"); write(self.d, "f", "2"); g("commit", "-qam", "wip")
        g("checkout", "-q", "main")
        cwd = os.getcwd()
        os.chdir(self.d)
        try:
            bs = {b["name"]: b for b in gittidy.branches("main", 60)}
        finally:
            os.chdir(cwd)
        self.assertTrue(bs["merged-one"]["merged"])
        self.assertFalse(bs["wip"]["merged"])

    def test_portwho(self):
        import socket
        s = socket.socket(); s.bind(("127.0.0.1", 0)); s.listen(1)
        port = s.getsockname()[1]
        rows = [r for r in portwho.listening() if r["port"] == port]
        s.close()
        self.assertEqual(len(rows), 1)
        self.assertIn(os.getpid(), [p for _, p in rows[0]["procs"]])


if __name__ == "__main__":
    unittest.main()
