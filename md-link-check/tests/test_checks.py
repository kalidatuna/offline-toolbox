import os
import tempfile
import unittest
from pathlib import Path

from md_link_check.scanner import Checker, discover, find_root, scan


class Project:
    """A throwaway folder tree written from a {relative path: text} mapping."""

    def __init__(self, files):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        for rel, text in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    def check(self, rel="README.md"):
        return Checker(str(self.root)).check_file(str(self.root / rel))

    def codes(self, rel="README.md"):
        return [(f.line, f.code) for f in self.check(rel)]

    def close(self):
        self._tmp.cleanup()


class CheckTests(unittest.TestCase):
    def project(self, files):
        project = Project(files)
        self.addCleanup(project.close)
        return project

    def test_clean_links(self):
        p = self.project(
            {
                "README.md": "\n".join(
                    [
                        "# Read Me",
                        "[a](docs/guide.md) [b](docs/) [c](./docs/guide.md#first-step)",
                        "[d](#read-me) [e](#top) [f](#) [g](docs/guide.md#user-content-first-step)",
                        "[h](docs/my%20notes.md) [i](/docs/guide.md?raw=true) [j](docs/guide.md#L3-L5)",
                        "[k](https://example.com/missing.md) [l](mailto:a@b.c) [m](//cdn.x/y.js)",
                        "[n](docs/guide.md#First-Step) [o](tool.py#anything)",
                        "[ref][r]",
                        "",
                        "[r]: docs/guide.md#first-step",
                    ]
                ),
                "docs/guide.md": "## First step\n",
                "docs/my notes.md": "",
                "tool.py": "",
            }
        )
        self.assertEqual(p.check(), [])

    def test_missing_file_with_suggestion(self):
        p = self.project({"README.md": "[x](docs/gude.md)", "docs/guide.md": ""})
        [finding] = p.check()
        self.assertEqual(finding.code, "missing-file")
        self.assertIn("did you mean docs/guide.md?", finding.message)
        self.assertEqual((finding.line, finding.column, finding.target), (1, 5, "docs/gude.md"))

    def test_missing_folder_component(self):
        p = self.project({"README.md": "[x](nope/guide.md)"})
        self.assertEqual(p.codes(), [(1, "missing-file")])

    def test_file_used_as_folder(self):
        p = self.project({"README.md": "[x](a.md/b.md)", "a.md": ""})
        self.assertEqual(p.codes(), [(1, "missing-file")])

    def test_case_mismatch_in_any_component(self):
        p = self.project({"README.md": "[x](Docs/guide.md)\n[y](docs/Guide.md)", "docs/guide.md": ""})
        self.assertEqual(p.codes(), [(1, "case-mismatch"), (2, "case-mismatch")])

    def test_one_finding_per_link(self):
        p = self.project({"README.md": "[x](GUIDE.md#nope)", "guide.md": "# Yes"})
        self.assertEqual(p.codes(), [(1, "case-mismatch")])

    def test_missing_anchor_same_and_other_file(self):
        p = self.project(
            {
                "README.md": "# Install\n[a](#instal) [b](other.md#usage) [c](other.md#usage-1)",
                "other.md": "## Usage\n",
            }
        )
        findings = p.check()
        self.assertEqual([f.code for f in findings], ["missing-anchor"] * 2)
        self.assertIn("did you mean #install?", findings[0].message)
        self.assertIn("other.md", findings[1].message)

    def test_html_anchor_and_link(self):
        p = self.project(
            {
                "README.md": '<a id="custom"></a>\n[a](#custom) <a href="x.md">x</a> <img src="logo.svg">',
                "x.md": "",
            }
        )
        self.assertEqual(p.codes(), [(2, "missing-file")])

    def test_outside_root(self):
        p = self.project({"docs/a.md": "[up](../README.md) [out](../../elsewhere.md)", "README.md": ""})
        self.assertEqual(p.codes("docs/a.md"), [(1, "outside-root")])

    def test_github_repository_routes_are_allowed(self):
        p = self.project(
            {
                "README.md": "[a](../../issues) [b](../../security/advisories/new) [c](../..) [d](../../nope)",
                "docs/a.md": "[e](../../../wiki/Home) [f](../../issues)",
            }
        )
        self.assertEqual(p.codes(), [(1, "outside-root")])
        self.assertEqual(p.codes("docs/a.md"), [(1, "outside-root")])

    def test_root_relative_links(self):
        p = self.project({"docs/a.md": "[ok](/README.md) [bad](/MISSING.md)", "README.md": ""})
        self.assertEqual(p.codes("docs/a.md"), [(1, "missing-file")])

    def test_empty_malformed_and_local_urls(self):
        p = self.project(
            {
                "README.md": "\n".join(
                    [
                        "[a]()",
                        "[b](two words.md)",
                        "[c](file:///Users/me/notes.md)",
                        "[d](C:/Users/me/notes.md)",
                    ]
                )
            }
        )
        self.assertEqual(
            p.codes(),
            [(1, "empty-link"), (2, "malformed-link"), (3, "local-file-url"), (4, "local-file-url")],
        )

    def test_undefined_reference(self):
        p = self.project({"README.md": "[a][missing] [b][Defined]\n\n[defined]: README.md"})
        [finding] = p.check()
        self.assertEqual((finding.code, finding.target), ("undefined-reference", "missing"))

    def test_definition_target_is_checked(self):
        p = self.project({"README.md": "[a][x]\n\n[x]: gone.md"})
        self.assertEqual(p.codes(), [(3, "missing-file")])


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.project = Project(
            {
                "README.md": "",
                "notes.markdown": "",
                "script.py": "",
                ".github/PULL_REQUEST_TEMPLATE.md": "",
                "node_modules/pkg/README.md": "",
                "drafts/wip.md": "",
                "docs/a.md": "",
            }
        )
        self.addCleanup(self.project.close)

    def rel(self, paths):
        return sorted(os.path.relpath(p, self.project.root).replace(os.sep, "/") for p in paths)

    def test_default_excludes(self):
        found = self.rel(discover([str(self.project.root)]))
        self.assertEqual(
            found,
            [".github/PULL_REQUEST_TEMPLATE.md", "README.md", "docs/a.md", "drafts/wip.md", "notes.markdown"],
        )

    def test_user_excludes(self):
        found = self.rel(discover([str(self.project.root)], excludes=["drafts", "*.markdown"]))
        self.assertNotIn("drafts/wip.md", found)
        self.assertNotIn("notes.markdown", found)

    def test_explicit_file_is_always_checked(self):
        target = str(self.project.root / "script.py")
        self.assertEqual(list(discover([target])), [target])

    def test_find_root_prefers_git_folder(self):
        (self.project.root / ".git").mkdir()
        self.assertEqual(find_root(str(self.project.root / "docs")), str(self.project.root))

    def test_scan_counts_and_ignores(self):
        (self.project.root / "README.md").write_text("[x](gone.md) []()")
        findings, checked = scan([str(self.project.root)], str(self.project.root), ignore=["empty-link"])
        self.assertEqual(checked, 5)
        self.assertEqual([f.code for f in findings], ["missing-file"])


if __name__ == "__main__":
    unittest.main()
