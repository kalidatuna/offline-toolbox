# Limitations

This is a static, line-based reading of GitHub Flavored Markdown, not a full
CommonMark parser. It is tuned to report links that are broken on github.com.

## Parsing

- A link must start and end its destination on one line. Link *text* may wrap
  across lines, but `[text](` followed by a destination on the next line is
  not read.
- Indented (four-space) code blocks are not detected. A link inside one is
  checked like normal text. Fenced code blocks are skipped.
- Reference links are only checked in the full `[text][label]` and collapsed
  `[label][]` forms. A bare `[label]` with no definition is ordinary text in
  Markdown, so it is not reported.
- Unused reference definitions are not reported.
- Heading anchors follow GitHub's rules: lowercase, punctuation removed,
  spaces become `-`, duplicates get `-1`, `-2`. Anchors are compared without
  regard to case. Rare inputs (emoji shortcodes, some combining marks) may
  differ slightly from GitHub's output.

## Paths and anchors

- Anchors are only verified in `.md` and `.markdown` targets. A fragment on
  any other file, such as `script.py#L10`, is accepted.
- A link to a folder is accepted if the folder exists. Its README is not
  opened to check a fragment.
- `?query` parts are ignored, except that `?plain=1#L5` skips the anchor check.
- Links that climb exactly two levels above the root into a GitHub page
  (`../../issues`, `../../wiki/Page`) are accepted without checking that the
  page exists.

## Site generators

MkDocs, Docusaurus, Jekyll, and similar tools resolve links differently from
GitHub: site-relative paths like `/guide/install`, `.mdx` files, custom heading
IDs (`## Title {#custom}`), and content indented under admonitions. Exclude
those sources with `--exclude`, or use the generator's own link checker.

## Not checked

- External URLs. Nothing is fetched over the network.
- Links in other file types (HTML pages, reStructuredText, notebooks).
- Images referenced from CSS or embedded as `data:` URIs.
