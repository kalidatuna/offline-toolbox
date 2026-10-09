"""Find Markdown files and check their local links."""

from __future__ import annotations

import difflib
import fnmatch
import os
import re
from collections.abc import Iterable, Iterator
from urllib.parse import unquote

from .model import Document, Finding, Link
from .parse import normalize_label, parse

MARKDOWN_SUFFIXES = (".md", ".markdown")
DEFAULT_EXCLUDES = (
    ".git",
    ".hg",
    ".svn",
    ".tox",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "site-packages",
    "vendor",
    "dist",
    "build",
)
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_DRIVE = re.compile(r"^[A-Za-z]:[\\/]")
_LINE_ANCHOR = re.compile(r"^L\d+(?:C\d+)?(?:-L\d+(?:C\d+)?)?$")
# github.com renders a file at /owner/repo/blob/<branch>/<path>, so a link that
# climbs exactly two levels above the repository root lands on a repository
# page such as ../../issues or ../../security/advisories/new.
GITHUB_ROUTES = frozenset(
    """actions activity archive blob branches commit commits community compare
    contributors deployments discussions forks graphs issues labels milestone
    milestones network packages projects pull pulls pulse raw releases security
    settings stargazers tags tree watchers wiki""".split()
)


def is_markdown(path: str) -> bool:
    return path.lower().endswith(MARKDOWN_SUFFIXES)


def find_root(start: str) -> str:
    """Nearest ancestor (inclusive) holding .git; otherwise ``start`` itself."""
    start = os.path.abspath(start)
    base = start if os.path.isdir(start) else os.path.dirname(start)
    current = base
    while True:
        if os.path.exists(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return base
        current = parent


def discover(paths: Iterable[str], excludes: Iterable[str] = ()) -> Iterator[str]:
    """Yield Markdown files under ``paths`` in a stable order.

    Explicit file arguments are always yielded. Directories are walked, skipping
    DEFAULT_EXCLUDES and any name or relative path matching ``excludes``.
    """
    patterns = list(excludes)

    def excluded(rel: str, name: str) -> bool:
        return any(fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(name, p) for p in patterns)

    seen: set[str] = set()
    for path in paths:
        path = os.path.abspath(path)
        if os.path.isfile(path):
            if path not in seen:
                seen.add(path)
                yield path
            continue
        for dirpath, dirnames, filenames in os.walk(path):
            rel_dir = os.path.relpath(dirpath, path)
            rel_dir = "" if rel_dir == "." else rel_dir.replace(os.sep, "/") + "/"
            dirnames[:] = sorted(
                d for d in dirnames if d not in DEFAULT_EXCLUDES and not excluded(rel_dir + d, d)
            )
            for name in sorted(filenames):
                full = os.path.join(dirpath, name)
                if is_markdown(name) and not excluded(rel_dir + name, name) and full not in seen:
                    seen.add(full)
                    yield full


class Checker:
    def __init__(self, root: str) -> None:
        self.root = os.path.normpath(os.path.abspath(root))
        self._documents: dict[str, Document | None] = {}
        self._listings: dict[str, list[str] | None] = {}

    # -- helpers -----------------------------------------------------------

    def display(self, path: str) -> str:
        rel = os.path.relpath(path, self.root)
        if rel == ".." or rel.startswith(".." + os.sep):
            return path
        return rel.replace(os.sep, "/")

    def _document(self, path: str) -> Document | None:
        if path not in self._documents:
            try:
                with open(path, encoding="utf-8", errors="replace") as handle:
                    self._documents[path] = parse(handle.read())
            except OSError:
                self._documents[path] = None
        return self._documents[path]

    def _listdir(self, directory: str) -> list[str] | None:
        if directory not in self._listings:
            try:
                self._listings[directory] = sorted(os.listdir(directory))
            except OSError:
                self._listings[directory] = None
        return self._listings[directory]

    def _inside_root(self, path: str) -> bool:
        try:
            return os.path.commonpath([self.root, path]) == self.root
        except ValueError:  # different drives on Windows
            return False

    def _is_github_route(self, target: str) -> bool:
        parts = os.path.relpath(target, self.root).split(os.sep)
        return parts[:2] == ["..", ".."] and (len(parts) == 2 or parts[2] in GITHUB_ROUTES)

    def locate(self, target: str) -> tuple[str, str | None, str | None]:
        """Resolve ``target`` (under root) one component at a time.

        Returns (status, actual_path, suggestion) where status is "ok",
        "case" (exists only with different letter case), or "missing".
        Listing each folder makes the check case-exact even on macOS and
        Windows, whose file systems ignore case by default.
        """
        rel = os.path.relpath(target, self.root)
        if rel == ".":
            return "ok", self.root, None
        current = self.root
        fixed: list[str] = []
        case_changed = False
        for part in rel.split(os.sep):
            entries = self._listdir(current)
            if entries is None:
                return "missing", None, None
            if part in entries:
                name = part
            else:
                folded = [e for e in entries if e.casefold() == part.casefold()]
                if not folded:
                    close = difflib.get_close_matches(part, entries, n=1, cutoff=0.6)
                    hint = "/".join(fixed + close[:1]) if close else None
                    return "missing", None, hint
                name = folded[0]
                case_changed = True
            fixed.append(name)
            current = os.path.join(current, name)
        return ("case" if case_changed else "ok"), current, None

    # -- checks ------------------------------------------------------------

    def check_file(self, path: str) -> list[Finding]:
        path = os.path.normpath(os.path.abspath(path))
        shown = self.display(path)
        doc = self._document(path)
        if doc is None:
            return [Finding(shown, 0, 0, "unreadable-file", "could not read file")]
        findings: list[Finding] = []
        for link in doc.links:
            finding = self._check_link(path, shown, link)
            if finding is not None:
                findings.append(finding)
        for use in doc.ref_uses:
            if normalize_label(use.label) not in doc.definitions:
                findings.append(
                    Finding(
                        shown,
                        use.line,
                        use.column,
                        "undefined-reference",
                        f"no definition for reference [{use.label}]; it renders as plain text",
                        use.label,
                    )
                )
        findings.sort(key=lambda f: (f.line, f.column, f.code))
        return findings

    def _check_link(self, path: str, shown: str, link: Link) -> Finding | None:
        dest = link.dest.strip()

        def finding(code: str, message: str) -> Finding:
            return Finding(shown, link.line, link.column, code, message, link.dest)

        if link.malformed:
            return finding(
                "malformed-link",
                "destination contains a space; encode it as %20 or wrap it in <...>",
            )
        if not dest:
            if link.kind == "definition":
                return None
            return finding("empty-link", f"{link.kind} has an empty destination")
        if dest.lower().startswith("file:") or _DRIVE.match(dest):
            return finding("local-file-url", "points at a path on one machine; use a relative link")
        if _SCHEME.match(dest) or dest.startswith("//"):
            return None  # external URL, mailto:, etc. are out of scope

        path_part, query, fragment = _split(dest)
        if not path_part:
            target = path
        else:
            if path_part.startswith("/"):
                target = os.path.normpath(os.path.join(self.root, path_part.lstrip("/")))
            else:
                target = os.path.normpath(os.path.join(os.path.dirname(path), path_part))
            if not self._inside_root(target):
                if self._is_github_route(target):
                    return None
                return finding(
                    "outside-root",
                    "resolves above the checked root; pass --root if that folder is intended",
                )
            status, actual, hint = self.locate(target)
            if status == "missing":
                message = f"not found: {self.display(target)}"
                if hint:
                    message += f" (did you mean {hint}?)"
                return finding("missing-file", message)
            assert actual is not None
            if status == "case":
                return finding(
                    "case-mismatch",
                    f"{self.display(target)} differs in letter case from {self.display(actual)}; "
                    "GitHub and Linux are case-sensitive",
                )
            target = actual

        if not fragment or "plain=1" in query:
            return None
        return self._check_fragment(target, fragment, finding)

    def _check_fragment(self, target: str, fragment: str, finding) -> Finding | None:
        if not (is_markdown(target) and os.path.isfile(target)):
            return None
        if fragment.lower() == "top" or _LINE_ANCHOR.match(fragment):
            return None
        wanted = fragment.lower()
        if wanted.startswith("user-content-"):
            wanted = wanted[len("user-content-") :]
        doc = self._document(target)
        if doc is None or wanted in doc.anchors:
            return None
        where = self.display(target)
        message = f"no heading or id '#{fragment}' in {where}"
        close = difflib.get_close_matches(wanted, sorted(doc.anchors), n=1, cutoff=0.6)
        if close:
            message += f" (did you mean #{close[0]}?)"
        return finding("missing-anchor", message)


def _split(dest: str) -> tuple[str, str, str]:
    fragment = ""
    query = ""
    if "#" in dest:
        dest, fragment = dest.split("#", 1)
    if "?" in dest:
        dest, query = dest.split("?", 1)
    return unquote(dest), query, unquote(fragment)


def scan(
    paths: Iterable[str],
    root: str,
    excludes: Iterable[str] = (),
    ignore: Iterable[str] = (),
) -> tuple[list[Finding], int]:
    """Check every Markdown file under ``paths``; return (findings, files_checked)."""
    checker = Checker(root)
    skip = set(ignore)
    findings: list[Finding] = []
    count = 0
    for path in discover(paths, excludes):
        count += 1
        findings.extend(f for f in checker.check_file(path) if f.code not in skip)
    return findings, count
