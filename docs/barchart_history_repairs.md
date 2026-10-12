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
git switch main
git pull --ff-only origin main
py -3 -m venv tools\barchart\.venv
$py = '.\tools\barchart\.venv\Scripts\python.exe'
& $py -m pip install playwright pytest tzdata
& $py -m playwright install chromium
$tool = 'tools\barchart\download_history_repairs.py'
& $py $tool plan
& $py $tool probe
```

`probe` opens a **visible** browser with an isolated persistent Chromium profile.
Log into Barchart manually there; it displays only visible, non-secret control
metadata. If the login page opens, complete login, then rerun `probe`. Check
whether the page has uniquely identified native Intraday, 1-minute and date
controls. If the site uses custom React/Angular controls or labels changed,
**stop**: submit the sanitized `CONTROL` output and screenshot for a reviewed
selector update. Never use blind click coordinates, skip a captcha or supply
login credentials to the script. The browser profile stays on your machine.

After the form selectors are confirmed, run exactly one live job. To download
without showing a Chromium window, add the optional `--headless` switch. It
uses the same saved browser profile that you authenticated in visible `probe`:

```powershell
& $py $tool once --headless
& $py $tool status
```

Check the first `progress.jsonl` record and the CSV (requested contract,
range, one minute, saved row count, first/last CT timestamps and SHA-256).
**Headless download has not yet been tested against a live Premier session**:
this first request is an experiment, not a guarantee it will succeed.

## Browser closes during download transfer

A `VERIFIED` line and a proposed CSV filename mean the download *started*;
they do **not** prove that the CSV completed. An error such as `Target page,
context or browser has been closed` may indicate page closure, browser crash,
or an interrupted transfer. The exact cause is not known from this message
alone, and the downloader must not count it as acquired.

As an isolation test, use your **installed Google Chrome** instead of the
bundled Playwright Chromium browser. Playwright officially supports Chrome
using `channel="chrome"`. The Chrome profile is intentionally separate
(`browser_profile_chrome`), so you may need to log in once:

```powershell
& $py $tool probe --channel chrome
# In the launched Chrome window, sign in to Barchart Premier if needed.
# Open the NMH23 historical-download page and press Enter in PowerShell.
& $py $tool once --channel chrome --inspect-on-error
& $py $tool status
```

The downloader's `BROWSER_DIAGNOSTIC` output records whether Playwright
observed a page crash, page closure, context closure, or a download event.
It does not save cookies or raw HTML. If the context has already closed,
cleanup will preserve the first error instead of replacing it with a second
exception from `ctx.close()`.

If both Chromium and Chrome fail, compare by manually using Barchart's
normal download form *inside the visible probe browser*, without running
`once`. Use the **same exact symbol** (`NMH23`), 1-minute interval and
dates (2022-10-17 through 2022-10-20) as the first pending request. A
manual successful download is diagnostic evidence only: it is **not** an
accepted or manifest-tracked acquisition and should not be copied to the
repair originals folder. Contact Barchart support if normal browser
downloads fail for the same historic window.

For low-level Chromium process-exit information on Windows, you can
temporarily set `$env:DEBUG='pw:browser'` before `once` and then
`Remove-Item Env:DEBUG` afterward. Do not post unredacted debug logs
or profile/session contents. Start with the concise `BROWSER_DIAGNOSTIC`.

Once Chrome works in visible mode, `once --channel chrome --headless`
can test headless **separately**. A visible success does not guarantee
headless access, and login/challenge handling remains manual.

If `once` reports `Browser download failed` immediately after a VERIFIED line,
the page controls worked but the browser reported an unsuccessful transfer. Stop
before `resume` and use the visible diagnostic mode:

```powershell
& $py $tool once --inspect-on-error
& $py $tool status
```

This prints Playwright's download failure reason and the suggested filename,
**then pauses with Chromium open on failure**. Inspect Barchart's on-page
message and Chrome Downloads (Ctrl+J); take a screenshot if appropriate,
without including passwords, cookies, or private account information. Return
to PowerShell and press Enter to close the browser. Only `once` in visible
mode supports this diagnostic flag; no request is considered acquired on
failure. No files are overwritten and no plan rebuild is needed.

If the site redirects to login, shows a challenge, blocks headless automation,
or changes its controls, the downloader must stop. It does not bypass login or
CAPTCHA. Close other browser instances using this automation profile and run
`& $py $tool probe` for a visible login. If needed, run a visible first
download with `& $py $tool once`.

Only after reviewing the first successful file, continue:

```powershell
& $py $tool resume --headless
& $py $tool status
& $py -m pytest -q tests\test_barchart_history_repairs.py
```

Omit `--headless` to use the original visible workflow. The flag is allowed
only for `once` and `resume`; `probe` stays visible for manual login.
Do not start two downloaders against the same profile or work directory.

**Headless means no browser window**, not a Windows background service. Leave
the PowerShell process and computer running during the downloads. Barchart
quota/rate limits and login expiration still apply.

All data stays in `$HOME\Documents\barchart-mnq-repairs\` by default:
`request_manifest.json` and its SHA-256 lock (immutable request plan),
`progress.jsonl` (append-only, verified per completed request),
`original_csv\` (original vendor download bytes copied without normalization),
and `browser_profile\` (browser sign-in state; never commit or share it).
The downloader refuses unknown existing files, changed hash, unsupported CSV
headers, malformed OHLCV, invalid timestamps, wrong symbol *when present in CSV*,
ambiguous controls, login walls, download errors, or suspicious filenames.
The strict minute parser supports the two observed Barchart formats
`YYYY/MM/DD HH:MM` and `YYYY-MM-DD HH:MM` (also the existing
`YYYY-MM-DD HH:MM:SS` format when seconds are zero). It still enforces the
manifest's Chicago CT date range, minute alignment, timezone/DST checks and
one-minute adjacency.
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
