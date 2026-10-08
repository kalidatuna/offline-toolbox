# Toolbox: 25 small, offline, privacy-first tools

No installs, no accounts, no network (except `sitecheck`, which exists to make requests). CLIs are Python 3.10+ stdlib only. Web tools are single HTML files: open in a browser, nothing is uploaded.

Why these: recurring complaints about online utilities are ads/trackers, uploading private files to unknown servers, and needing an account for a 10-second task. Each tool here removes one of those.

## CLI (`cli/`), run with `python3 cli/<name>.py --help`

| Tool | Solves |
|---|---|
| `dupefind` | Find duplicate files by content; optionally move extras to a folder (never deletes) |
| `diskhog` | "Where did my disk go?" biggest dirs/files with bars |
| `bulkrename` | Regex/number/case rename, dry-run by default, one-command `--undo` |
| `secretscan` | Catch API keys, tokens, private keys before you commit (masked output, CI exit code) |
| `envdiff` | Compare `.env` vs `.env.example` by key; never prints values |
| `portwho` | What's holding port 3000? Optionally free it |
| `gittidy` | List merged/stale local branches; safely delete merged |
| `logsift` | Collapse a giant log into distinct error patterns with counts |
| `csvpeek` | CSV health report: types, nulls, mixed types, ragged rows, duplicates |
| `jwtpeek` | Decode a JWT locally; flag expired / alg=none / no exp |
| `cronexplain` | Cron expression to English plus next run times |
| `mdtoc` | Generate/refresh a Markdown table of contents (GitHub anchors, idempotent) |
| `tzmeet` | Meeting slots inside everyone's working hours across time zones (DST-aware) |
| `sitecheck` | Batch uptime + TLS-expiry check for cron/CI |
| `pwcheck` | Offline password strength check and secure generator |
| `splitbill` | Split shared expenses; suggested payments to settle up (exact decimal math) |
| `loanplan` | Loan payment, total interest, savings from extra payments |

## Web (`web/`), open `index.html`

| Tool | Solves |
|---|---|
| `jsontool` | Format/validate (with line+col of error), minify, sort keys, path query, JSON to CSV |
| `textdiff` | Line diff with word-level highlights |
| `regex` | Live regex tester: matches, groups, replace preview, common patterns |
| `invoice` | Freelancer invoice with totals/tax/discount, print to PDF, autosaves locally |
| `subs` | Subscription tracker: monthly/yearly cost, renewals due soon, CSV export |
| `imgtool` | Resize/compress/convert images; re-encoding strips EXIF (GPS) |
| `focus` | Pomodoro timer with session log and notifications |
| `textstats` | Word count, reading time, readability, keyword density, platform length limits |

## Tests

```bash
python3 -m unittest discover -s tests -v  # CLI and regression tests
node tests/test_web.mjs       # logic of the 8 web tools (extracted from each page)
```

Web UIs were also smoke-tested in a real browser (no console errors).

GitHub Actions runs the Python suite on Python 3.10 and 3.12, and the browser logic tests on Node.js 22, for pull requests and pushes to `main`.

## Known limits

- `portwho` is Linux-only (uses `ss`); other users' processes need sudo to show.
- `secretscan` is regex + entropy heuristics: expect some misses and false positives; it is a safety net, not an audit.
- `jwtpeek` does not verify signatures by design (no keys). Do not use it as proof a token is valid.
- `imgtool` "Download all" saves files one by one (no zip library, to stay offline and single-file).
- `textstats` readability is tuned for English.
- `bulkrename` refuses destinations that already exist, including another source in the same plan, to avoid overwriting file contents.
- `diskhog` counts hard-linked data once and attributes it to the first file location visited.
- `splitbill` requires nonnegative amounts in whole cents and unique participant names. Rounding cents go to the first beneficiaries in input order. Its greedy settlement suggestions do not guarantee the minimum possible number of payments.
- `pwcheck gen` requires a password length of at least 4; passphrase word counts must be nonnegative.
