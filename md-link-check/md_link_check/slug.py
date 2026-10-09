"""GitHub-style heading anchors.

GitHub builds an anchor from the rendered heading text: lowercase it, drop
punctuation and symbols (keeping letters, digits, ``_`` and ``-``), and turn
each space into ``-``. Repeated anchors get ``-1``, ``-2``, ... suffixes.
"""

from __future__ import annotations

import html
import re

_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_INLINE_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_REF_LINK = re.compile(r"\[([^\]]*)\]\[[^\]]*\]")
_TAG = re.compile(r"<[^>]+>")
_UNDERSCORE_EMPHASIS = re.compile(r"(?<![\w\\])_+|(?<!\\)_+(?!\w)")
_ESCAPE = re.compile(r"\\([!-/:-@\[-`{-~])")
_NOT_SLUG = re.compile(r"[^\w\- ]")


def split_code_spans(text: str) -> list[tuple[bool, str]]:
    """Split ``text`` into (is_code, content) parts using CommonMark code spans."""
    parts: list[tuple[bool, str]] = []
    i = start = 0
    n = len(text)
    while i < n:
        if text[i] != "`" or (i and text[i - 1] == "\\"):
            i += 1
            continue
        j = i
        while j < n and text[j] == "`":
            j += 1
        close = _find_backtick_run(text, j, j - i)
        if close < 0:
            i = j
            continue
        parts.append((False, text[start:i]))
        content = text[j:close]
        if len(content) > 1 and content[0] == " " and content[-1] == " " and content.strip():
            content = content[1:-1]
        parts.append((True, content))
        i = start = close + (j - i)
    parts.append((False, text[start:]))
    return parts


def _find_backtick_run(text: str, pos: int, length: int) -> int:
    n = len(text)
    while pos < n:
        if text[pos] != "`":
            pos += 1
            continue
        end = pos
        while end < n and text[end] == "`":
            end += 1
        if end - pos == length:
            return pos
        pos = end
    return -1


def heading_text(raw: str) -> str:
    """Approximate the text GitHub renders for a heading's Markdown source."""
    out = []
    for is_code, part in split_code_spans(raw):
        if is_code:
            out.append(part)
            continue
        part = _IMAGE.sub("", part)
        part = _INLINE_LINK.sub(r"\1", part)
        part = _REF_LINK.sub(r"\1", part)
        part = _TAG.sub("", part)
        part = _UNDERSCORE_EMPHASIS.sub("", part)
        part = _ESCAPE.sub(r"\1", part)
        out.append(html.unescape(part))
    return "".join(out).strip()


def slugify(text: str) -> str:
    """Return the anchor for already-rendered heading text (no de-duplication)."""
    return _NOT_SLUG.sub("", text.strip().lower()).replace(" ", "-")


class Slugger:
    """Assign unique anchors in document order, like GitHub does."""

    def __init__(self) -> None:
        self._seen: dict[str, int] = {}

    def add(self, raw_heading: str) -> str:
        base = slugify(heading_text(raw_heading))
        if base not in self._seen:
            self._seen[base] = 0
            return base
        count = self._seen[base]
        while True:
            count += 1
            candidate = f"{base}-{count}"
            if candidate not in self._seen:
                break
        self._seen[base] = count
        self._seen[candidate] = 0
        return candidate
