"""Extract links, reference definitions, and anchors from Markdown text.

This is a line-oriented approximation of CommonMark/GFM, not a full parser.
It skips fenced code blocks, inline code spans, HTML comments, and YAML front
matter so that example links in code are not reported.
"""

from __future__ import annotations

import html
import re

from .model import Document, Link, RefUse
from .slug import Slugger

# Fences inside list items may be indented further than 3 spaces.
_FENCE_OPEN = re.compile(r"^[ \t]*(`{3,}|~{3,})(.*)$")
_FENCE_CLOSE = re.compile(r"^[ \t]*(`{3,}|~{3,})[ \t]*$")
_QUOTE_PREFIX = re.compile(r"^(?: {0,3}>[ \t]?)+")
_ATX = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?[ \t]*$")
_ATX_CLOSING = re.compile(r"(?:^|[ \t]+)#+$")
_SETEXT = re.compile(r"^ {0,3}(=+|-+)[ \t]*$")
_NOT_PARAGRAPH = re.compile(r"^ {0,3}(?:[-*+][ \t]|\d{1,9}[.)][ \t]|>|<|\||#)")
_DEFINITION = re.compile(r"^ {0,3}\[((?:[^\]\\]|\\.)+)\]:[ \t]*(<[^>]*>|\S+)")
_REF_USE = re.compile(r"(?<![\w\]\\])\[((?:[^\[\]\\]|\\.)*)\]\[((?:[^\[\]\\]|\\.)*)\](?![(:])")
_HTML_LINK = re.compile(
    r"<(?:a|area|link)\b[^>]*?\shref\s*=\s*(?:\"([^\"]*)\"|'([^']*)')"
    r"|<(?:img|source|video|audio|iframe|script)\b[^>]*?\ssrc\s*=\s*(?:\"([^\"]*)\"|'([^']*)')",
    re.IGNORECASE,
)
_HTML_ID = re.compile(r"<[a-zA-Z][^>]*?\s(?:id|name)\s*=\s*(?:\"([^\"]*)\"|'([^']*)')", re.IGNORECASE)
_ESCAPE = re.compile(r"\\([!-/:-@\[-`{-~])")
_SPACE = re.compile(r"\s+")
_ENTITY = re.compile(r"&(?:#[0-9]{1,7}|#[xX][0-9a-fA-F]{1,6}|[A-Za-z][A-Za-z0-9]{1,31});")


def normalize_label(label: str) -> str:
    """Reference labels match case-insensitively with collapsed whitespace."""
    return _SPACE.sub(" ", label.strip()).casefold()


def mask_code_spans(line: str) -> str:
    """Replace inline code spans with spaces, keeping column positions."""
    chars = list(line)
    i, n = 0, len(line)
    while i < n:
        if line[i] != "`" or _escaped(line, i):
            i += 1
            continue
        j = i
        while j < n and line[j] == "`":
            j += 1
        run = j - i
        k = j
        close = -1
        while k < n:
            if line[k] != "`":
                k += 1
                continue
            end = k
            while end < n and line[end] == "`":
                end += 1
            if end - k == run:
                close = k
                break
            k = end
        if close < 0:
            i = j
            continue
        for p in range(i, close + run):
            chars[p] = " "
        i = close + run
    return "".join(chars)


def mask_comments(line: str, in_comment: bool) -> tuple[str, bool]:
    """Blank out HTML comments; ``in_comment`` carries state across lines."""
    out = []
    i, n = 0, len(line)
    while i < n:
        if in_comment:
            k = line.find("-->", i)
            if k < 0:
                out.append(" " * (n - i))
                i = n
            else:
                out.append(" " * (k + 3 - i))
                i = k + 3
                in_comment = False
        else:
            k = line.find("<!--", i)
            if k < 0:
                out.append(line[i:])
                i = n
            else:
                out.append(line[i:k])
                i = k
                in_comment = True
    return "".join(out), in_comment


def _escaped(text: str, pos: int) -> bool:
    count = 0
    pos -= 1
    while pos >= 0 and text[pos] == "\\":
        count += 1
        pos -= 1
    return count % 2 == 1


def _find_opener(line: str, close: int) -> int:
    """Index of the '[' matching the ']' at ``close`` on this line, or -1."""
    depth = 0
    for i in range(close - 1, -1, -1):
        ch = line[i]
        if _escaped(line, i):
            continue
        if ch == "]":
            depth += 1
        elif ch == "[":
            if depth == 0:
                return i
            depth -= 1
    return -1


def parse_destination(line: str, start: int) -> tuple[str, int, bool] | None:
    """Parse an inline link destination beginning at ``start`` (just after '(').

    Returns (destination, start index, malformed) or None when the text is not
    a complete link on this line.
    """
    n = len(line)
    j = start
    while j < n and line[j] in " \t":
        j += 1
    if j < n and line[j] == "<":
        end = line.find(">", j + 1)
        if end < 0:
            return None
        return line[j + 1 : end], j + 1, False
    begin = j
    depth = 0
    while j < n:
        ch = line[j]
        if ch == "\\" and j + 1 < n:
            j += 2
            continue
        if ch in " \t":
            break
        if ch == "(":
            depth += 1
        elif ch == ")":
            if depth == 0:
                break
            depth -= 1
        j += 1
    if j >= n:
        return None
    dest = line[begin:j]
    if line[j] == ")":
        return dest, begin, False
    # Whitespace after the destination must be followed by a title or ')'.
    k = j
    while k < n and line[k] in " \t":
        k += 1
    if k < n and line[k] in "\"')(":
        return dest, begin, False
    close = line.find(")", k)
    if close < 0:
        return None
    return line[begin:close].rstrip(), begin, True


def _unescape(text: str) -> str:
    """Apply backslash escapes and entity references, as CommonMark does."""
    return _decode_entities(_ESCAPE.sub(r"\1", text))


def _decode_entities(text: str) -> str:
    # Only complete references ending in ';' (unlike html.unescape on its own,
    # which would turn the query string "a=1&copy=2" into "a=1©=2").
    return _ENTITY.sub(lambda m: html.unescape(m.group(0)), text)


def _front_matter_end(lines: list[str]) -> int:
    if not lines or lines[0].strip() != "---":
        return 0
    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            return i + 1
    return 0


def parse(text: str) -> Document:
    doc = Document()
    slugger = Slugger()
    lines = text.splitlines()
    fence: tuple[str, int] | None = None
    in_comment = False
    paragraph: list[str] = []

    for index in range(_front_matter_end(lines), len(lines)):
        raw = lines[index]
        lineno = index + 1

        if fence is not None:
            m = _FENCE_CLOSE.match(_QUOTE_PREFIX.sub("", raw))
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= fence[1]:
                fence = None
            continue
        if not in_comment:
            m = _FENCE_OPEN.match(_QUOTE_PREFIX.sub("", raw))
            if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
                fence = (m.group(1)[0], len(m.group(1)))
                paragraph = []
                continue

        line, in_comment = mask_comments(mask_code_spans(raw), in_comment)
        _collect_html_ids(line, doc)
        body = _QUOTE_PREFIX.sub("", raw)

        if not line.strip():
            if not raw.strip():
                paragraph = []
            continue

        heading = _ATX.match(body)
        if heading:
            content = _ATX_CLOSING.sub("", heading.group(2) or "").strip()
            doc.anchors.add(slugger.add(content).lower())
            paragraph = []
        elif paragraph and _SETEXT.match(body):
            doc.anchors.add(slugger.add(" ".join(paragraph)).lower())
            paragraph = []
            continue
        elif _NOT_PARAGRAPH.match(body):
            paragraph = []
        else:
            paragraph.append(body.strip())

        definition = _DEFINITION.match(line)
        if definition:
            label, dest = definition.group(1), definition.group(2)
            if not label.startswith("^"):  # footnote definitions are not links
                if dest.startswith("<") and dest.endswith(">"):
                    dest = dest[1:-1]
                doc.definitions.setdefault(normalize_label(label), dest)
                column = definition.start(2) + 1
                doc.links.append(Link(lineno, column, _unescape(dest), "definition"))
            paragraph = []
            continue

        labels = _collect_inline_links(line, lineno, doc)
        _collect_html_links(line, lineno, doc)
        _collect_ref_uses(line, lineno, doc, labels)

    return doc


def _collect_inline_links(line: str, lineno: int, doc: Document) -> list[tuple[int, int]]:
    """Record inline links; return the (start, end) spans of their labels."""
    labels = []
    for match in re.finditer(r"\]\(", line):
        close = match.start()
        if _escaped(line, close):
            continue
        parsed = parse_destination(line, close + 2)
        if parsed is None:
            continue
        dest, begin, malformed = parsed
        opener = _find_opener(line, close)
        kind = "image" if opener > 0 and line[opener - 1] == "!" else "link"
        if opener >= 0:
            labels.append((opener, close))
        doc.links.append(Link(lineno, begin + 1, _unescape(dest), kind, malformed))
    return labels


def _collect_html_links(line: str, lineno: int, doc: Document) -> None:
    for match in _HTML_LINK.finditer(line):
        for group in range(1, 5):
            if match.group(group) is not None:
                dest = _decode_entities(match.group(group))
                doc.links.append(Link(lineno, match.start(group) + 1, dest, "html"))
                break


def _collect_html_ids(line: str, doc: Document) -> None:
    for match in _HTML_ID.finditer(line):
        value = match.group(1) if match.group(1) is not None else match.group(2)
        if value:
            doc.anchors.add(value.lower())


def _collect_ref_uses(
    line: str, lineno: int, doc: Document, labels: list[tuple[int, int]]
) -> None:
    for match in _REF_USE.finditer(line):
        text, label = match.group(1), match.group(2)
        label = label if label.strip() else text
        if not label.strip() or label.startswith("^"):
            continue
        is_image = match.start() > 0 and line[match.start() - 1] == "!"
        if not is_image and any(a < match.start() and match.end() <= b for a, b in labels):
            continue  # bracketed words inside another link's label
        doc.ref_uses.append(RefUse(lineno, match.start() + 1, label))
