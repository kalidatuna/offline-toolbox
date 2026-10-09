import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args, cwd=None):
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    return subprocess.run(
        [sys.executable, "-m", "md_link_check", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )


class CliTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        (self.dir / "docs").mkdir()
        (self.dir / "docs" / "guide.md").write_text("# Guide\n")

    def write(self, text):
        (self.dir / "README.md").write_text(text)

    def test_clean_exit_zero(self):
        self.write("[g](docs/guide.md#guide)")
        result = run(str(self.dir))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("No findings in 2 Markdown file(s)", result.stdout)

    def test_findings_exit_one_with_locations(self):
        self.write("ok\n[g](docs/guid.md)")
        result = run(str(self.dir))
        self.assertEqual(result.returncode, 1)
        self.assertIn("README.md:2:5: missing-file: not found: docs/guid.md", result.stdout)
        self.assertIn("1 finding(s) in 1 of 2 Markdown file(s)", result.stdout)

    def test_json_output(self):
        self.write("[g](docs/guide.md#nope)")
        result = run(str(self.dir), "--json")
        self.assertEqual(result.returncode, 1)
        [finding] = json.loads(result.stdout)
        self.assertEqual(
            {k: finding[k] for k in ("file", "line", "column", "code", "target")},
            {"file": "README.md", "line": 1, "column": 5, "code": "missing-anchor", "target": "docs/guide.md#nope"},
        )

    def test_default_path_is_current_folder(self):
        self.write("[x](gone.md)")
        result = run(cwd=self.dir)
        self.assertEqual(result.returncode, 1)
        self.assertIn("README.md:1:5: missing-file", result.stdout)

    def test_ignore_and_exclude(self):
        self.write("[x](gone.md)")
        self.assertEqual(run(str(self.dir), "--ignore", "missing-file").returncode, 0)
        self.assertEqual(run(str(self.dir), "--exclude", "README.md").returncode, 0)

    def test_root_option_widens_scope(self):
        (self.dir / "docs" / "guide.md").write_text("[up](../README.md)")
        self.write("")
        docs = str(self.dir / "docs")
        self.assertEqual(run(docs).returncode, 1)
        self.assertEqual(run(docs, "--root", str(self.dir)).returncode, 0)

    def test_invalid_input_exit_two(self):
        self.assertEqual(run(str(self.dir / "missing")).returncode, 2)
        self.assertEqual(run(str(self.dir), "--ignore", "not-a-code").returncode, 2)
        self.assertEqual(run(str(self.dir), "--root", str(self.dir / "nope")).returncode, 2)


if __name__ == "__main__":
    unittest.main()
