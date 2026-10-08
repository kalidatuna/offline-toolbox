# Markdown Link Check

An offline checker for the links inside a repository's Markdown files. It finds
relative links to files that do not exist, `#anchors` that match no heading,
paths that only work on case-insensitive disks, and reference links with no
definition. No network access, no third-party Python packages.

Install it from this folder of the toolbox (Python 3.10+):

```sh
pip install "git+https://github.com/kalidatuna/offline-toolbox#subdirectory=md-link-check"
```

```sh
md-link-check                  # scan the current folder
md-link-check README.md docs/  # scan specific files and folders
md-link-check --json           # machine-readable findings
```

Without installing, run `python3 -m md_link_check` from this folder, or set
`PYTHONPATH` to it.

Example output:

```text
README.md:3:13: case-mismatch: docs/Setup.md differs in letter case from docs/setup.md; GitHub and Linux are case-sensitive
README.md:4:19: missing-anchor: no heading or id '#instalation' in README.md (did you mean #installation?)
docs/usage.md:12:5: missing-file: not found: docs/gude.md (did you mean docs/guide.md?)
3 finding(s) in 2 of 9 Markdown file(s)
```

The command exits 0 when every link resolves, 1 for findings, and 2 for invalid
input. Each finding is `file:line:column: code: message`.

## What it checks

| Code | Meaning |
| --- | --- |
| `missing-file` | A relative or `/root-relative` link points to nothing |
| `case-mismatch` | `Docs/Guide.md` exists only as `docs/guide.md`: fine on macOS and Windows, a 404 on GitHub |
| `missing-anchor` | `#fragment` matches no heading or HTML `id`/`name` in the target file, using GitHub's anchor rules |
| `undefined-reference` | `[text][label]` has no `[label]: url` definition, so it renders as plain text |
| `empty-link` | `[text]()` |
| `malformed-link` | `[text](my file.md)`: an unescaped space stops the link from rendering |
| `outside-root` | `../../other-repo/file.md` climbs above the repository |
| `local-file-url` | `file:///Users/me/...` or `C:/...` points at one machine |

External URLs (`https:`, `mailto:`, ...) are not fetched. GitHub repository
links such as `../../issues` are accepted.

Links are read from inline links and images, reference definitions, and
HTML `href`/`src` attributes. Fenced code, inline code, HTML comments, and YAML
front matter are skipped, so examples in code do not produce findings.

## Options

```sh
python3 -m md_link_check --exclude 'docs/site/*' --exclude CHANGELOG.md
python3 -m md_link_check --ignore outside-root
python3 -m md_link_check docs --root .
```

- `--exclude GLOB` skips files or folders by name or relative path. `.git`,
  `node_modules`, virtual environments, `vendor`, `dist`, and `build` are
  always skipped.
- `--ignore CODE` drops one finding code from the report.
- `--root DIR` sets where `/absolute` links resolve and how far `../` may climb.
  The default is the nearest folder containing `.git`, else the first path.

## Use in CI or pre-commit

GitHub Actions, after `actions/checkout` and `actions/setup-python`:

```yaml
- run: pip install "git+https://github.com/kalidatuna/offline-toolbox#subdirectory=md-link-check"
- run: md-link-check
```

pre-commit, as a local hook in `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: md-link-check
        name: md-link-check
        entry: md-link-check
        language: python
        additional_dependencies:
          - "md-link-check @ git+https://github.com/kalidatuna/offline-toolbox#subdirectory=md-link-check"
        files: \.(md|markdown)$
        pass_filenames: false
```

## Tests

```sh
python3 -m unittest discover -s tests -v
```

The checker was also run against several large public repositories with
translated tables of contents (Cyrillic, CJK, Kannada, accented Latin), where
every sampled finding was a link that is broken on GitHub. See
[limitations](docs/limitations.md) for what it does not handle.
