# EXP-001 — Score-band baseline analysis

## Purpose

Measure whether the frozen 0–100 confluence score ranks the existing 2023,
2024, and 2025 baseline trades usefully. This is diagnostic research only:
do not alter score weights, entries, stops, targets, or the historical control
set.

## Required inputs

Use the three archived `trades.csv` files created by the completed baseline
runs. The ledgers (rather than a scored-bar cache) are the required inputs, so
the command does not run any stage of the feature or backtest pipeline.

Each ledger must include the normal `src/backtest.py` trade-output fields:
`direction`, `raw_score`, `net_result_points`, `net_result_r`, TP-hit flags,
`stop_hit`, `mfe_points`, and `mae_points`. `minutes_held` is reported when it
is present.

## Run

From `/docker/trade-alerts` on the trading VPS, first update the repository,
then point the command at the actual three archived ledgers:

```bash
git pull --ff-only origin main
source .venv/bin/activate
python scripts/run_exp001_score_bands.py \
  --ledger 2023=/docker/trade-alerts/data/results/research_runs/<2023-baseline-run>/trades.csv \
  --ledger 2024=/docker/trade-alerts/data/results/research_runs/<2024-baseline-run>/trades.csv \
  --ledger 2025=/docker/trade-alerts/data/results/research_runs/<2025-baseline-run>/trades.csv
```

The exact run is fast and ledger-only; tmux is not needed. It writes:

- `data/reports/EXP-001_score-bands-baseline/exp001_score_band_results.json`
- `data/reports/EXP-001_score-bands-baseline/EXP-001_score-band-baseline.md`

## Interpretation rules

- The fixed buckets are `<50`, `50–59`, `60–69`, `70–79`, `80–89`, and
  `90–100`; the report includes only buckets that actually contain trades.
- A bucket with fewer than 30 trades is explicitly exploratory.
- Monotonicity is assessed only across buckets with at least 30 trades and
  requires non-decreasing expectancy *and* profit factor.
- Compare the annual and long/short segments before relying on a pooled result.
- The score remains ordinal confluence, never a predicted win probability.

## Closeout

After the command completes, preserve the generated JSON and Markdown next to
the archived ledgers (or otherwise archive their hashes), then update the
EXP-001 status in `refine-roadmap.md` with the observed findings only. Do not
mark score calibration as complete merely because one score band is profitable.
