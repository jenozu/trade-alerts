# Barchart Historical MNQ Workflow

This document records the Windows-side historical data acquisition workflow used to expand Phase 12 backtesting beyond the history available from ProjectX.

## Why Barchart is being used

ProjectX remains the live/production market-data source, but the current account/API path did not expose expired MNQ contracts through contract search and returned zero historical bars when inferred expired contract IDs were requested directly. That made ProjectX unsuitable as the sole source for multi-year historical research.

Barchart Premier exposes expired MNQ quarterly contracts and 1-minute intraday downloads. Historical research therefore uses Barchart raw files while live production continues to use ProjectX.

## Source-of-truth rule

The original Barchart CSV downloads are immutable source material.

Do not edit, resave, normalize in place, or commit the raw files to Git. Derived Parquet files, stitched datasets, audits, and backtest outputs are generated separately.

## Barchart export format observed

Raw columns:

```text
Time,Open,High,Low,Latest,Change,%Change,Volume
```

Normalization mapping:

```text
Time    -> timestamp (America/Chicago -> UTC)
Open    -> open
High    -> high
Low     -> low
Latest  -> close
Volume  -> volume
source  -> BARCHART
symbol  -> MNQ
contract -> manifest contract
```

Every observed CSV includes one Barchart metadata/footer row similar to:

```text
Downloaded from Barchart.com as of ... CDT
```

That row has no OHLCV values and is removed only in the derived normalized copy.

Barchart also commonly returns the prior calendar day's 17:00 Chicago bar when a requested trading date begins at the CME Globex session open. The audit showed a systematic -420 minute offset for 112 files, consistent with the prior-day 17:00 CT session start. Two holiday-start cases began at 17:00 on the requested calendar date. These were treated as expected futures-session behavior rather than corruption.

## Initial five-year archive

The initial manifest covers quarterly MNQ contracts from late 2021 through 2026-09-04:

```text
2022: NMH22 NMM22 NMU22 NMZ22
2023: NMH23 NMM23 NMU23 NMZ23
2024: NMH24 NMM24 NMU24 NMZ24
2025: NMH25 NMM25 NMU25 NMZ25
2026: NMH26 NMM26 NMU26
```

Contract windows intentionally overlap by five calendar days near quarterly roll periods. The overlap is retained so the eventual continuous series can choose explicit rollover boundaries rather than blindly concatenating files.

The download manifest contains 133 jobs, split into approximately 14-calendar-day chunks to remain comfortably below Barchart's 20,000-record-per-request limit.

## Proven acquisition result — 2026-09-05

Playwright acquisition completed successfully:

```text
Complete: 133/133
Pending: 0
Errors: 0
Timeouts: 0
```

Raw audit results:

- 0 missing expected files
- 0 extra CSV files
- no critical file errors
- 1,819,656 one-minute intervals observed during the raw-file audit
- 376 two-minute intervals observed
- 1,341 gaps greater than two minutes observed; these include expected session/weekend/holiday closures and must remain subject to session-aware validation before final research certification
- largest observed raw gap: 4,381 minutes
- every file contained one Barchart footer/non-market row

## Proven normalization result — 2026-09-05

Normalization completed successfully:

```text
Successful files: 133 / 133
Failed files: 0
Normalized rows: 1,821,506
Footer rows removed: 133
Numeric rows removed: 0
Duplicates removed: 0
NORMALIZATION PASSED
```

The original Barchart CSV files were not modified.

## Repository tooling

The reproducible tooling lives under:

```text
tools/barchart/
```

Current scripts:

- `generate_manifest.py` — generates the 133-job quarterly-contract manifest.
- `download_barchart_history.py` — resumable Playwright downloader using a persistent authenticated Barchart browser profile.
- `audit_manifest.py` — checks manifest continuity, order, overlap, duplicate filenames, and status.
- `audit_barchart_history.py` — validates raw downloaded CSV presence, headers, OHLCV integrity, timestamps, duplicates, and gap statistics.
- `inspect_barchart_warnings.py` — explains systematic footer rows and requested-date/session offsets.
- `normalize_barchart_history.py` — writes separate standardized Parquet copies and a normalization audit.
- `build_contract_parquets.py` — merges normalized chunks into one audited Parquet per quarterly contract, rejects conflicting duplicate timestamps, removes identical chunk-overlap duplicates, preserves raw prices, hashes inputs/outputs, and reports continuity/gap statistics.

Local browser profiles, manifests, raw market data, normalized Parquet files, contract-level Parquets, and generated audits are intentionally Git-ignored.

## Windows setup

Use a dedicated virtual environment. The local workflow was developed with:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install playwright pandas pyarrow
python -m playwright install chromium
```

The downloader uses a persistent Playwright profile so the user can log into Barchart Premier manually once and reuse the authenticated session. Do not commit that browser profile.

## Contract-level merge stage

After normalization succeeds, build one contract-level Parquet per quarterly contract before choosing rollover boundaries:

```powershell
python tools\barchart\build_contract_parquets.py `
  --manifest manifest.csv `
  --input-dir normalized-barchart `
  --output-dir contract-parquets `
  --audit-output contract_parquets_audit.json
```

If the Barchart tools are being run from the standalone Windows downloader directory rather than a local clone of this repository, copy or invoke the committed script from `tools/barchart/` and point the arguments at the local manifest/normalized directories.

The builder deliberately does not fill session/weekend/holiday gaps and does not back-adjust prices. Duplicate timestamps created by adjacent download chunks are allowed only when the market values are identical; conflicting duplicates fail the build. Every output contract Parquet receives SHA-256 evidence in the audit.

The contract build is a prerequisite for rollover selection. Do not stitch the five-year continuous series if any contract fails.

## Next stage

Do not run a five-year backtest directly against the 133 chunk files.

The next research-data stages are:

1. Run `build_contract_parquets.py` and certify all quarterly contract files.
2. Review per-contract timestamp order, duplicate-removal counts, session gaps, coverage, and hashes in `contract_parquets_audit.json`.
3. Determine and document explicit quarterly rollover timestamps using the overlap windows and a reproducible rule.
4. Stitch the quarterly contracts into one non-back-adjusted continuous MNQ research series.
5. Write a stitch audit containing contract order, rollover timestamps, row counts, overlaps/gaps, and source metadata.
6. Run staged Phase 12 baselines against the resulting historical series.
7. Archive run metadata/results while keeping market data outside Git.

## Research discipline

Do not tune the strategy against the short 2026 ProjectX sample before establishing the Barchart multi-year baseline. Preserve the current strategy/config as the baseline, run longer horizons first, and evaluate changes with held-out / walk-forward testing as required by `PHASE12_BACKTESTING_PLAN.md`.
