# Phase 12 — Staged Backtesting / Calibration Execution Plan

This document is the operational companion to **Phase 12 — Formal Backtesting / Calibration** in `phases.md`.

The strategy/backtest engine already exists. The purpose of this plan is to define **how to expand from a one-month smoke backtest into 3-month, 6-month, and 12-month research without overfitting or corrupting futures rollover history**.

## Current proven baseline

- `run_pipeline.py` executes the complete 20-stage research pipeline.
- Stage 20 is the historical backtest.
- `src/backtest.py` produces the trade ledger and summary metrics.
- ProjectX historical acquisition exists in `fetch_projectx_history.py`.
- Multi-contract stitching exists in `stitch_projectx_history.py`.
- The first VPS end-to-end backtest was run on 30,360 MNQ 1-minute bars covering roughly 2026-08-05 through 2026-09-04.
- That first run is a **pipeline proof / baseline only**, not a calibration result.

## Research principle

Do not tune the strategy against a single short sample and then call the result validated.

Use progressively larger horizons:

1. **1 month** — smoke test and trade-ledger inspection.
2. **3 months** — first meaningful stability check.
3. **6 months** — multi-regime and rollover validation.
4. **12 months** — primary historical calibration sample.
5. **Walk-forward / out-of-sample** — final validation before accepting parameter changes.

Keep NQ and MNQ histories separate. Preserve exact source, contract, date range, config version, and output artifacts for every run.

---

# Stage A — 1-month baseline

## Goal

Prove the pipeline, inspect individual trades, and identify obvious implementation/data issues before collecting larger history.

## Existing VPS input

At the time this plan was added, the VPS already had a 30,360-row ProjectX MNQ 1-minute snapshot covering approximately one month:

```text
data/raw/projectx/2026-09-04_1512_mnq_1m.parquet
```

## Command

```bash
cd /docker/trade-alerts
source .venv/bin/activate

python run_pipeline.py \
  --input data/raw/projectx/2026-09-04_1512_mnq_1m.parquet \
  --source PROJECTX \
  --symbol MNQ \
  --timezone UTC
```

Do **not** use `--stop-after`; the run should reach `[20/20] RUN BACKTEST`.

## Record

- exact input file
- start/end timestamps
- bar count
- trade count
- win rate
- expectancy points
- expectancy R
- profit factor
- warning/degraded-analysis state
- config commit SHA
- `data/results/backtest/trades.csv`
- `data/results/backtest/backtest_metrics.json`
- `data/results/pipeline/latest_run.json`

## Do not tune yet

The one-month run is too small for strategy calibration. Use it to inspect whether trades and exits make sense.

---

# Stage B — 3-month backtest

## Goal

Get the first broader view of strategy stability and increase the number of trades enough to begin segmentation analysis.

## Data acquisition rule

If the full 3-month period belongs to one explicit quarterly contract, fetch that contract directly.

Example pattern:

```bash
python fetch_projectx_history.py \
  --symbol MNQ \
  --contract-name CONTRACT_NAME \
  --start START_UTC \
  --end END_UTC \
  --output data/raw/projectx/CONTRACT_NAME_3m_1m.csv
```

If the requested period crosses a futures rollover, **do not request one current contract across the whole period and assume it is continuous**. Fetch each quarterly contract separately and stitch them explicitly.

## Backtest command

```bash
python run_pipeline.py \
  --input data/raw/projectx/MNQ_3m_RESEARCH_INPUT.csv \
  --source PROJECTX \
  --symbol MNQ \
  --timezone UTC
```

## Review

In addition to headline metrics, segment results by:

- long vs short
- reversal vs continuation
- raw score band
- DOL direction/alignment
- session context
- volatility regime
- exit reason
- month

Do not change parameters solely because one subgroup had a small losing sample.

---

# Stage C — 6-month backtest

## Goal

Test the system across multiple contracts, changing volatility conditions, and at least one rollover boundary.

## Required data discipline

Fetch explicit quarterly contract files separately.

Pattern:

```bash
python fetch_projectx_history.py \
  --symbol MNQ \
  --contract-name CONTRACT_A \
  --start START_A_UTC \
  --end END_A_UTC \
  --output data/raw/projectx/CONTRACT_A_1m.csv

python fetch_projectx_history.py \
  --symbol MNQ \
  --contract-name CONTRACT_B \
  --start START_B_UTC \
  --end END_B_UTC \
  --output data/raw/projectx/CONTRACT_B_1m.csv
```

Then stitch using explicit rollover timestamps:

```bash
python stitch_projectx_history.py \
  --contract CONTRACT_A=data/raw/projectx/CONTRACT_A_1m.csv \
  --contract CONTRACT_B=data/raw/projectx/CONTRACT_B_1m.csv \
  --rollover ROLLOVER_TIMESTAMP_UTC \
  --symbol MNQ \
  --output data/raw/projectx/mnq_6m_continuous_1m.csv \
  --audit-output data/raw/projectx/mnq_6m_continuous_1m.audit.json
```

For more than two contracts, repeat `--contract` in chronological order and provide exactly N-1 `--rollover` values.

## Backtest

```bash
python run_pipeline.py \
  --input data/raw/projectx/mnq_6m_continuous_1m.csv \
  --source PROJECTX \
  --symbol MNQ \
  --timezone UTC
```

Inspect the stitch audit before trusting metrics.

---

# Stage D — 12-month backtest

## Goal

Build the main historical sample used for formal Phase 12 calibration.

## Requirements

- explicit quarterly contracts
- validated rollover boundaries
- no price back-adjustment unless deliberately introduced and documented
- exact source/contract metadata preserved
- duplicate and gap diagnostics reviewed
- exact stitched input archived
- exact strategy/session configs preserved with the run

Use the same `fetch_projectx_history.py` + `stitch_projectx_history.py` workflow as the 6-month stage, extended across all required contracts.

Backtest the final stitched file through `run_pipeline.py` with no `--stop-after`.

---

# Metrics to capture for every horizon

Minimum headline metrics:

- number of trades
- win rate
- average/median R
- expectancy in points
- expectancy in R
- profit factor
- TP1 / TP2 / TP3 / TP4 hit rates
- stop rate
- no-trade rate where applicable
- MFE
- MAE
- maximum adverse streak / drawdown if supported

Required segmentation:

- direction: long / short
- setup family: reversal / continuation
- score band
- DOL classification/alignment
- bias state
- session context
- volatility regime
- month / contract
- entry and exit reason

A higher score band should outperform lower score bands over a meaningful sample before score thresholds are treated as calibrated.

---

# Calibration workflow

Do not optimize all parameters at once.

Recommended order:

1. Validate data and rollover correctness.
2. Validate trade-generation logic by reviewing individual ledger rows.
3. Establish baseline metrics with current config.
4. Identify one hypothesis for improvement.
5. Change one parameter family at a time.
6. Re-run the same training sample.
7. Reject changes that only improve a narrow period/regime.
8. Validate accepted candidates on a held-out period.
9. Compare historical behavior to Phase 11 shadow-mode observations.
10. Only then update production strategy configuration.

Parameters listed in `phases.md` for calibration include displacement thresholds, SNR thresholds/weights, support/resistance confluence weights, scorer weights, confidence bands, DOL thresholds/weights, swing parameters, FVG significance, RVOL thresholds, stop buffers, room-to-run filters, exit model, and target priorities.

---

# Walk-forward / out-of-sample rule

The 12-month dataset must not be repeatedly tuned and then used as its own proof.

A simple starting discipline is:

- earlier portion = development/calibration
- later untouched portion = validation

For larger datasets, prefer rolling walk-forward windows so parameters are evaluated across multiple unseen periods.

Never choose parameters solely because they maximize historical net profit.

---

# Run archive convention

For each meaningful backtest, preserve a run folder outside Git-tracked market data, for example:

```text
data/results/research_runs/
  2026-09-04_1m_baseline/
  2026-09-XX_3m_baseline/
  2026-09-XX_6m_baseline/
  2026-09-XX_12m_baseline/
```

Each run should contain or reference:

- input path and hash if practical
- date range
- contract list
- rollover audit
- Git commit SHA
- strategy config
- sessions config
- trades ledger
- metrics JSON
- pipeline audit
- notes on warnings/degraded state

Do not commit large market datasets or secrets to Git.

---

# Phase 12 completion gates

Phase 12 is not complete merely because the pipeline can produce a profitable backtest.

Required before completion:

- multi-month explicit-contract dataset created and audited
- 1m / 3m / 6m / 12m baseline runs recorded
- sufficient trade sample for meaningful segmentation
- rollover boundaries validated
- walk-forward or held-out evaluation completed
- score bands checked for monotonic usefulness
- historical results compared against Phase 11 shadow-mode observations
- accepted parameter changes are stable across regimes
- final configs and evidence committed/documented
- `phases.md` updated with final Phase 12 evidence

---

# Historical-source update — Barchart multi-year archive

ProjectX remains the live/production data source, but the current ProjectX account/API path did not provide usable expired-contract history for older MNQ contracts. Phase 12 historical research therefore now has a separate Barchart acquisition path documented in `docs/BARCHART_HISTORY_WORKFLOW.md`.

As of 2026-09-05, the Barchart workflow has proven:

- 133 / 133 requested 1-minute quarterly-contract CSV chunks downloaded successfully
- 0 download errors and 0 timeouts
- 0 missing files and 0 critical raw-file audit errors
- 1,821,506 normalized rows across the 133 files
- 133 Barchart footer rows removed only from derived normalized copies
- 0 numeric rows removed
- 0 duplicates removed
- raw Barchart CSV files preserved untouched
- Barchart `Time` interpreted as `America/Chicago` and converted to UTC
- Barchart `Latest` mapped to normalized `close`
- quarterly contract windows intentionally overlap around rollover periods

This is **not yet a completed five-year research dataset**. The remaining data-engineering work is to merge normalized chunks per contract, determine explicit rollover timestamps, stitch the quarterly contracts into one audited non-back-adjusted MNQ series, and then run staged Phase 12 baselines and held-out/walk-forward validation.

Do not mark Phase 12 complete based on data acquisition alone.
