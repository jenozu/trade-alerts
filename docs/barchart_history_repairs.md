# Barchart Premier individual-contract repair acquisition (not data acceptance)

This isolated Windows downloader does **not** change `run_isolated_feature_build.py`,
normalize history, write to VPS, or resume strategy research. The old downloader
cannot safely be reused: it marks nonempty arbitrary CSV files `complete` and
checks headers only. No published repair draft was present on `main` during audit.

## Why these windows

The frozen configuration requires 20 *previous* trading sessions for the
same-minute-of-day relative-volume baseline, minimum five previous sessions,
and generates 1m, 5m, 15m, 30m, 1h, 4h and 1d context. Swing confirmation
uses left/right pivots (2/2 and 5/5); multi-timeframe FVG/IFVG tracking,
weekly/previous-session levels, and structure state are potentially path-
dependent. These features do not imply a provably sufficient finite warmup.
The manifest requests **56 calendar days before each incoming contract's first
retained rollover date, plus four days afterward**. This is an explicit,
conservative *data-acquisition hypothesis* giving room for more than 20 ordinary
trading sessions, not a certified warmup cutoff or permission to score trades.
There are 13 incoming contracts, including six with only 960 unused Monday bars;
the priority is to preserve all earlier exact-contract history, not to assume
those Mondays suffice. Date ranges are CT calendar days, and four-inclusive-day
chunks have an absolute maximum of 5,760 minute timestamps (less than both the
old 10,000-record and the newer 20,000-record limits).

Barchart pages: https://help.barchart.com/support/solutions/articles/242748-how-can-i-download-historical-data-
(10,000-record older help article) and
https://www.barchart.com/futures/quotes/NMM23/historical-download
(the current historical-download page states 20,000; confirms Chicago CT futures
timestamps, intraday qualifies only new-last-price trades and excludes some
trade types). A daily Premier quota may require several sessions to finish.

## Setup on Windows PowerShell

```powershell
cd $HOME\Documents
if (!(Test-Path .\trade-alerts)) { git clone https://github.com/jenozu/trade-alerts.git }
cd .\trade-alerts
git pull --ff-only origin main
py -3.12 -m venv .venv-barchart-repairs
.\.venv-barchart-repairs\Scripts\python.exe -m pip install playwright pytest
.\.venv-barchart-repairs\Scripts\python.exe -m playwright install chromium
$tool = 'tools\barchart\download_history_repairs.py'
.\.venv-barchart-repairs\Scripts\python.exe $tool plan
.\.venv-barchart-repairs\Scripts\python.exe $tool probe
```

`probe` opens a **visible** browser with an isolated persistent Chromium profile.
Log into Barchart manually there; it displays only visible, non-secret control
metadata. If the login page opens, complete login, then rerun `probe`. Check
whether the page has uniquely identified native Intraday, 1-minute and date
controls. If the site uses custom React/Angular controls or labels changed,
**stop**: submit the sanitized `CONTROL` output and screenshot for a reviewed
selector update. Never use blind click coordinates, skip a captcha or supply
login credentials to the script. The browser profile stays on your machine.

After the form selectors are confirmed, run exactly one live job:

```powershell
.\.venv-barchart-repairs\Scripts\python.exe $tool once
.\.venv-barchart-repairs\Scripts\python.exe $tool status
```

Check its `progress.jsonl` record and the CSV (requested contract, range, one
minute, saved row count, first/last CT timestamps and SHA-256). Then continue:

```powershell
.\.venv-barchart-repairs\Scripts\python.exe $tool resume
.\.venv-barchart-repairs\Scripts\python.exe $tool status
.\.venv-barchart-repairs\Scripts\python.exe -m pytest -q tests\test_barchart_history_repairs.py
```

All data stays in `$HOME\Documents\barchart-mnq-repairs\` by default:
`request_manifest.json` and its SHA-256 lock (immutable request plan),
`progress.jsonl` (append-only, verified per completed request),
`original_csv\` (original vendor download bytes copied without normalization),
and `browser_profile\` (browser sign-in state; never commit or share it).
The downloader refuses unknown existing files, changed hash, unsupported CSV
headers, malformed OHLCV, invalid timestamps, wrong symbol *when present in CSV*,
ambiguous controls, login walls, download errors, or suspicious filenames.
It never marks missing/empty days as complete and never overwrites existing CSVs.
Any interruption can be resumed after reviewing the reason it stopped.

## Acceptance must remain separate

The downloader validates the **request and file format**, not exchange-history
completeness. After acquisition, inspect original CSV/chunk manifests and compare
source overlap on the exact contract with original locked history. Classify
Chicago CT/DST, bar timestamps and exchange sessions (including holidays,
Globex breaks and omitted no-trade minutes); test required same-contract context
for all downstream features, including stateful HTF swings, FVG and structure.
Only then may new versioned derivatives be considered. Never overwrite frozen
artifacts or feed downloads directly into an unreviewed backtest.
