# Barchart Historical MNQ Workflow

This document records the historical data acquisition and engineering workflow used to expand Phase 12 backtesting beyond the history available from ProjectX.

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
Time     -> timestamp (America/Chicago -> UTC)
Open     -> open
High     -> high
Low      -> low
Latest   -> close
Volume   -> volume
source   -> BARCHART
symbol   -> MNQ
contract -> manifest contract
```

Every observed CSV includes one Barchart metadata/footer row similar to:

```text
Downloaded from Barchart.com as of ... CDT
```

That row has no OHLCV values and is removed only in the derived normalized copy.

Barchart also commonly returns the prior calendar day's 17:00 Chicago bar when a requested trading date begins at the CME Globex session open. The workflow therefore assigns bars by CME-style trading date before merging adjacent download chunks.

## Historical contract archive

The archive used for the certified series contains:

```text
2022: NMH22 NMM22 NMU22 NMZ22
2023: NMH23 NMM23 NMU23 NMZ23
2024: NMH24 NMM24 NMU24 NMZ24
2025: NMH25 NMM25 NMU25 NMZ25
2026: NMH26 NMM26 NMU26
```

This produces coverage beginning in late December 2021 because the first contract window starts before calendar 2022.

The result is approximately **4 years 8.5 months** of continuous coverage through 2026-09-04. It should not be described as a literal trailing five-year dataset unless older 2021 contracts are added later.

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
- 1,341 gaps greater than two minutes observed; these include expected session/weekend/holiday closures
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

## Proven contract-build result — 2026-09-05

The normalized chunk Parquets were merged into one Parquet per quarterly contract using manifest-window ownership based on CME trading date.

Certified result:

```text
Successful contracts: 19 / 19
Failed contracts: 0
Rows across outputs: 1,774,466
Rows ownership-trimmed: 47,040
Empty owned chunks: 0
Duplicates removed after trim: 0
CONTRACT BUILD PASSED
```

Audit:

```text
data/raw/barchart/contract_parquets_audit.json
```

## Proven rollover-analysis result — 2026-09-05

Adjacent quarterly contracts were compared using daily trading volume in their overlap windows.

Deterministic rule:

> Roll at the CME session open preceding the first trading date where the new contract has higher daily volume than the old contract for two consecutive overlapping trading days.

Certified result:

```text
Contracts: 19
Expected rollovers: 18
Succeeded: 18
Failed: 0
```

All 18 selected boundaries used:

```text
confirmed_volume_crossover
```

No fallback/unconfirmed rollover was used.

Audit:

```text
data/raw/barchart/rollover_analysis.json
```

## Proven continuous-series result — 2026-09-05

The 19 quarterly contracts were stitched into one non-back-adjusted continuous MNQ 1-minute research series.

Certified result:

```text
Contracts: 19
Rollover boundaries: 18
Rows: 1,663,671
UTC coverage: 2021-12-20T06:00:00+00:00 -> 2026-09-04T20:59:00+00:00
Duplicate timestamps: 0
Null OHLCV: 0
Price adjustment: none
```

Final dataset:

```text
data/raw/barchart/mnq_continuous_1m.parquet
```

Stitch audit:

```text
data/raw/barchart/mnq_continuous_1m.audit.json
```

Final dataset SHA-256:

```text
fa8b33621d74a4016c35f0fa19df75f1d6adc864f71f794c391bbe4e4620cf8a
```

The continuous dataset is now certified for Phase 12 baseline research. It is not committed to Git.

## Repository tooling

The reproducible tooling lives under:

```text
tools/barchart/
```

Current scripts include:

- `generate_manifest.py` — generates the quarterly-contract download manifest.
- `download_barchart_history.py` — resumable Playwright downloader using a persistent authenticated Barchart browser profile.
- `audit_manifest.py` — checks manifest continuity, order, overlap, duplicate filenames, and status.
- `audit_barchart_history.py` — validates raw downloaded CSV presence, headers, OHLCV integrity, timestamps, duplicates, and gap statistics.
- `inspect_barchart_warnings.py` — explains systematic footer rows and requested-date/session offsets.
- `normalize_barchart_history.py` — writes standardized Parquet copies and a normalization audit.
- `build_contract_parquets.py` — assigns chunk ownership by CME trading date and produces one audited Parquet per quarterly contract.
- `analyze_barchart_rollovers.py` — determines explicit rollovers from confirmed daily-volume crossover.
- `stitch_barchart_history.py` — creates the final non-back-adjusted continuous research series and stitch audit.

Local browser profiles, manifests, raw market data, normalized Parquet files, contract-level Parquets, continuous datasets, and generated audits are intentionally Git-ignored.

## Current Phase 12 handoff

The Barchart data-engineering stage is complete enough for serious backtesting.

Do **not** immediately optimize strategy parameters.

The required next sequence is maintained in `docs/PHASE12_BACKTESTING_PLAN.md`:

1. implement automatic research-run archiving
2. run untouched 6-month baseline
3. run untouched 12-month baseline
4. run year-by-year baselines
5. run the full certified multi-year baseline
6. perform segmentation analysis
7. test exit models as a controlled experiment family
8. change one parameter family at a time
9. validate candidates on held-out / walk-forward periods
10. only then reconcile with Phase 11 live/shadow observations and update production configuration

## Research discipline

Preserve the current strategy/config as the baseline. Establish broad historical behavior before tuning. Keep every meaningful research run reproducible and archived with the input hash, Git SHA, config snapshots, metrics, trade ledger, and rollover references.
