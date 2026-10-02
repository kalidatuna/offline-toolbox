#!/usr/bin/env python3
"""mdtoc - generate or refresh a Markdown table of contents (GitHub anchors).

  mdtoc.py README.md            print TOC
  mdtoc.py README.md --write    insert/update between <!-- toc --> and <!-- /toc --> markers
  options: --min 2 --max 4
"""
import argparse
import re
import sys

START, END = "<!-- toc -->", "<!-- /toc -->"


def slug(text, seen):
    s = re.sub(r"[`*_~]|\[([^\]]*)\]\([^)]*\)", lambda m: m.group(1) or "", text).strip().lower()
    s = re.sub(r"[^\w\- ]", "", s).replace(" ", "-")
    n = seen.get(s, 0)
    seen[s] = n + 1
    return s if n == 0 else f"{s}-{n}"


def headings(md):
    out, fence, seen = [], False, {}
    for line in md.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fence = not fence
        if fence:
            continue
        m = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if m:
            out.append((len(m.group(1)), m.group(2), slug(m.group(2), seen)))
    return out


def build_toc(md, lo=2, hi=4):
    hs = [h for h in headings(md) if lo <= h[0] <= hi]
    return "\n".join(f"{'  ' * (lvl - lo)}- [{t}](#{a})" for lvl, t, a in hs)


def inject(md, toc):
    block = f"{START}\n{toc}\n{END}"
    if START in md and END in md:
        return re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, md, flags=re.S)
    return block + "\n\n" + md


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--min", type=int, default=2)
    ap.add_argument("--max", type=int, default=4)
    a = ap.parse_args(argv)
    with open(a.file, encoding="utf-8") as f:
        md = f.read()
    toc = build_toc(md.replace(START, "").replace(END, ""), a.min, a.max)
    if a.write:
        new = inject(md, toc)
        with open(a.file, "w", encoding="utf-8") as f:
            f.write(new)
        print(f"updated {a.file}")
    else:
        print(toc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
