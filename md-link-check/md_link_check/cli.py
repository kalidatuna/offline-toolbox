"""Command line interface."""

from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__
from .model import CODES
from .scanner import find_root, scan


def build_parser() -> argparse.ArgumentParser:
    codes = "\n".join(f"  {code:<20} {text}" for code, text in CODES.items())
    parser = argparse.ArgumentParser(
        prog="md-link-check",
        description="Check relative links and #anchors in Markdown files, offline.",
        epilog=f"finding codes:\n{codes}\n\nexit status: 0 clean, 1 findings, 2 invalid input",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "paths", nargs="*", default=["."], help="Markdown files or folders to scan (default: .)"
    )
    parser.add_argument(
        "--root",
        help="folder that /absolute links resolve against and links may not leave "
        "(default: nearest folder containing .git, else the first path)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="skip files or folders whose name or relative path matches (repeatable)",
    )
    parser.add_argument(
        "--ignore",
        action="append",
        default=[],
        metavar="CODE",
        choices=sorted(CODES),
        help="do not report this finding code (repeatable)",
    )
    parser.add_argument("--json", action="store_true", help="write findings as a JSON list")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    # Headings and paths may be in any script; never crash on a narrow console.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    parser = build_parser()
    args = parser.parse_args(argv)
    for path in args.paths:
        if not os.path.exists(path):
            parser.error(f"no such file or folder: {path}")
    if args.root is not None and not os.path.isdir(args.root):
        parser.error(f"--root is not a folder: {args.root}")
    root = args.root or find_root(args.paths[0])

    findings, checked = scan(args.paths, root, excludes=args.exclude, ignore=args.ignore)

    if args.json:
        print(json.dumps([f.to_dict() for f in findings], indent=2))
    else:
        for f in findings:
            print(f"{f.file}:{f.line}:{f.column}: {f.code}: {f.message}")
        if findings:
            files = len({f.file for f in findings})
            print(f"{len(findings)} finding(s) in {files} of {checked} Markdown file(s)")
        else:
            print(f"No findings in {checked} Markdown file(s)")
    return 1 if findings else 0
