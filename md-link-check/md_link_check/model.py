"""Data types shared by the parser, scanner, and command line interface."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

CODES = {
    "missing-file": "relative link points to a file or folder that does not exist",
    "case-mismatch": "path exists only with different letter case",
    "missing-anchor": "#fragment matches no heading or HTML id in the target",
    "undefined-reference": "[text][label] has no matching [label]: definition",
    "empty-link": "link destination is empty, e.g. [text]()",
    "malformed-link": "destination has an unescaped space, so the link does not render",
    "outside-root": "relative link resolves above the checked root",
    "local-file-url": "file: or drive-letter URL points at one machine's disk",
    "unreadable-file": "a Markdown file could not be read",
}


@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    column: int
    code: str
    message: str
    target: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Link:
    line: int
    column: int
    dest: str
    kind: str  # "link", "image", "definition", "html"
    malformed: bool = False


@dataclass(frozen=True)
class RefUse:
    line: int
    column: int
    label: str


@dataclass
class Document:
    links: list[Link] = field(default_factory=list)
    ref_uses: list[RefUse] = field(default_factory=list)
    definitions: dict[str, str] = field(default_factory=dict)
    anchors: set[str] = field(default_factory=set)
