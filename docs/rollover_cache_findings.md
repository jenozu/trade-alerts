# Frozen 2025 cache rollover findings — 2026-10-05

## Evidence and research gate

User-run, read-only VPS inspection of `2025_warmup_92d` verified the recorded
raw, scored and strategy-config hashes. Raw and scored both contain 441,015
rows, six contract segments and five matching marked contract transitions;
neither has duplicate timestamps or missing contract labels. Their timestamp
types differ (raw microseconds, cache nanoseconds), but actual timestamp and
contract values align at every row. The initial dtype-sensitive equality failure
was an inspection error, not a source-value discrepancy.

Cached ATR matches a 14-bar true-range rolling mean computed over the unadjusted
stitched tape, including the previous contract's close, at every boundary:

| New contract / first timestamp UTC | Cached ATR = cross-contract ATR |
| --- | --- |
| NMH25 / 2024-12-16 23:00 | 24.732142857142858 |
| NMM25 / 2025-03-17 22:00 | 18.875 |
| NMU25 / 2025-06-16 05:00 | 22.732142857142858 |
| NMZ25 / 2025-09-15 22:00 | 20.321428571428573 |
| NMH26 / 2025-12-15 23:00 | 22.017857142857142 |

The boundary snapshots also show persistent old-contract swing levels and some
FVG/MSS context. ATR cross-contract contamination is demonstrated; the complete
scope and duration of other state contamination still need verification. This
does not establish that the raw OHLCV is corrupt or quantify changes in returns.
The manifest lists 14 feature modules but omits the generation/orchestration path.
Recorded hashes preserve identity; they do not certify causal feature correctness.

R7 remains blocked. Preserve the original cache and historical ledgers as producer
controls; do not recertify or overwrite them. Rebuild corrected features separately
using independent contract segments, then verify raw identity, boundary isolation,
availability and warmup before constructing a corrected research baseline. Other
years must be audited using their existing artifacts; this finding alone does not
justify rebuilding the completed 2023 pipeline.

## Preventive pipeline correction

`run_pipeline.py` is a single-contract path. It now rejects multiple contract
labels or rollover segments before single-contract validation/resampling.
CSV and Parquet labels are inspected before metadata attachment; an explicit
contract cannot conceal a stitched tape or contradict a known input label.
Single-contract CSV labels are retained when no override is supplied. Partially
missing known contract labels fail closed; legacy entirely unlabelled inputs
retain their prior support and cannot be claimed as independently certified.

The existing `run_rollover_pipeline.py` remains the separate-contract route.
This guard prevents the unsafe orchestration path, but does not rebuild a cache,
fix frozen features in place, or cover custom callers invoking feature modules
directly. The existing rollover CLI expects stitched CSV with segment IDs starting
at zero; the preserved year slice has offset IDs, so prepare a new explicit
isolated runner/input before requesting a VPS rebuild.

Twelve regression cases cover labelled mixed CSV/Parquet, metadata concealment,
single-contract preservation, conflicts, missing labels, multiple segments,
legacy inputs and rejection before feature/output generation. Related suite:
52 passed, 6 warnings. Full regression: **697 passed, 583 warnings in 13.28s**.
Warnings remain reported NumPy timedelta compatibility debt.

## Additional VPS evidence

The updated v2 suite passed on the VPS: 685 passed, 583 warnings. The bounded
January comparison at `../replays/january-v2-20261005T172958Z` retained source
hashes and passed standalone lock verification. V1 produced one trade; v2 rejected
the January 29 short with structural risk 26.75 > 25, first-obstacle room
0.75 < 25, and TP1 asymmetry 0.03 < 1.00. This is real rejection-path evidence,
not a positive historical v2 execution or performance validation. The replay
reused the frozen features described above and remains diagnostic only.

The preventive guard subsequently passed 697 tests on the VPS (user-reported).
The next bounded regeneration task is documented in
[isolated_rollover_check.md](isolated_rollover_check.md); it precedes any full-year
corrected-cache build. Original controls remain preserved.
