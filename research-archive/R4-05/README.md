# R4.5 — Full-Universe Scoring Experiments

## Status

All 12 model-year experiments completed and independently verified.

Historical periods: 2023, 2024, 2025.

Four scoring configurations were evaluated for each year.

The original historical baseline trade ledgers were reproduced.

## Method

Existing historical feature datasets were reused.

A memory-bounded implementation scored historical data in batches
and executed the backtest over the complete chronological sequence.

The optimized implementation passed regression tests and
historical baseline verification.

## Interpretation

All four configurations were evaluated retrospectively.

Observed differences do not establish prospective performance.

Additional out-of-sample validation is required before adopting
changes to production scoring weights.

The consolidated stop_rate metric was unavailable in the generated
summary and must not be interpreted as zero.

No historical source datasets were modified.
