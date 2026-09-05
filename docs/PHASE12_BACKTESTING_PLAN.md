# Phase 12 — Staged Backtesting / Calibration Execution Plan

This document is the operational companion to **Phase 12 — Formal Backtesting / Calibration** in `phases.md`.

The strategy/backtest engine already exists. The purpose of this plan is to define **how to expand from a one-month smoke backtest into multi-month and multi-year research without overfitting or corrupting futures rollover history**.

## Current proven baseline

- `run_pipeline.py` executes the complete 20-stage research pipeline.
- Stage 20 is the historical backtest.
- `src/backtest.py` produces the trade ledger and summary metrics.
- ProjectX remains the live/production source.
- Barchart is now the historical source for expired MNQ quarterly contracts.
- The first VPS end-to-end ProjectX backtest was run on 30,360 MNQ 1-minute bars covering roughly 2026-08-05 through 2026-09-04.
- The later active-contract ProjectX sample covered only about two months and is not a valid 6-month sample.
- A certified continuous Barchart MNQ dataset now exists on the VPS at `data/raw/barchart/mnq_continuous_1m.parquet`.

## Certified Barchart research dataset — 2026-09-05

The historical-data engineering path is now complete enough to begin serious Phase 12 baseline testing.

Certified evidence:

- 133 / 133 Barchart 1-minute download chunks completed.
- 1,821,506 normalized rows across the chunk-level Parquets.
- 19 / 19 quarterly contract Parquets built successfully.
- 18 / 18 adjacent quarterly rollovers selected by confirmed daily-volume crossover.
- Continuous stitched dataset rows: **1,663,671**.
- UTC coverage: **2021-12-20 06:00:00+00:00 through 2026-09-04 20:59:00+00:00**.
- Contracts represented: **19**.
- Rollover boundaries: **18**.
- Duplicate timestamps: **0**.
- Null OHLCV cells: **0**.
- Price adjustment: **none**.
- Final dataset SHA-256: `fa8b33621d74a4016c35f0fa19df75f1d6adc864f71f794c391bbe4e4620cf8a`.
- Stitch audit: `data/raw/barchart/mnq_continuous_1m.audit.json`.
- Rollover audit: `data/raw/barchart/rollover_analysis.json`.
- Contract-build audit: `data/raw/barchart/contract_parquets_audit.json`.

This is a **multi-year dataset of about 4 years 8.5 months**, not a literal trailing five years. Do not describe it as a full five-year sample unless older 2021 contracts are added later.

## Research principle

Do not tune the strategy against a single short sample and then call the result validated.

Preserve the current strategy/config as the untouched baseline first. Establish broader baseline behavior before changing thresholds, weights, exits, or setup rules.

Keep NQ and MNQ histories separate. Preserve exact source, contract/date range, config version, Git SHA, and output artifacts for every meaningful run.

---

# Required execution sequence from the current checkpoint

This sequence supersedes the earlier idea of immediately running larger backtests without first making result preservation automatic.

1. **Build automatic research-run archiving.**
   - Do this before any serious 6-month / 12-month / year-by-year / full-history run.
   - Existing latest-result files must remain available for compatibility, but every meaningful run must also be copied into a unique immutable run directory.

2. **Run an untouched 6-month baseline.**
   - Use the certified Barchart continuous dataset.
   - Do not alter strategy parameters first.
   - Record complete metrics, trade ledger, configs, input hash, rollover references, Git SHA, and warnings.

3. **Run an untouched 12-month baseline.**
   - Same current strategy/config.
   - No calibration changes between the 6-month and 12-month baseline runs.

4. **Run year-by-year baselines.**
   - Evaluate stability across distinct market regimes.
   - Compare direction, score bands, setup families, DOL/bias states, displacement, structure shift, FVG context, session, exit reason, MFE/MAE, and drawdown behavior.

5. **Run the full certified multi-year baseline.**
   - Use the complete `mnq_continuous_1m.parquet` dataset.
   - Treat this as a broad behavior/stability sample, not a dataset to optimize repeatedly without holdout discipline.

6. **Perform segmentation analysis before tuning.**
   - Identify which features actually discriminate performance over meaningful sample sizes.
   - Re-check score-band monotonicity.
   - Compare long vs short and continuation vs reversal behavior.
   - Quantify regime dependence rather than reacting to one bad month.

7. **Run exit-model experiments as a separate controlled family.**
   Compare at least:
   - current full-position TP4 / stop model
   - TP1 then breakeven, runner to TP4
   - 25% at TP1 / TP2 / TP3 / TP4
   - partial at TP1 then breakeven on the runner
   - 50% at TP1 then breakeven runner to TP4

   Compare expectancy, profit factor, drawdown, average/median R, MFE/MAE capture, and robustness — not only win rate.

8. **Change one parameter family at a time.**
   - Every candidate must have a written hypothesis.
   - Reject improvements that are isolated to a narrow period or regime.

9. **Use held-out / walk-forward validation.**
   - Do not repeatedly optimize the same 12-month or full-history sample and then use that same sample as proof.
   - Preserve untouched validation windows.

10. **Only after historical validation, reconcile with Phase 11 shadow/live observations and update production configuration.**

Do not mark Phase 12 complete merely because one larger backtest is profitable.

---

# Stage A — Existing short-sample smoke baseline

## Goal

Prove the pipeline, inspect individual trades, and identify obvious implementation/data issues before using longer history.

The one-month and roughly two-month ProjectX runs already served this purpose. They are pipeline/behavior checks, not calibration evidence.

Previously observed on the roughly two-month active-contract sample:

- about 93–94 trades
- win rate about 27.7%
- expectancy about +9.3 points / +0.37R
- profit factor about 1.51
- exit behavior was effectively all-or-nothing TP4 vs stop
- displacement showed stronger discrimination than several other context flags
- score-band monotonicity was not established

Do not tune from this sample alone.

---

# Stage B — 6-month untouched Barchart baseline

## Goal

Test the current strategy across multiple contracts, multiple regimes, and rollover boundaries using the certified continuous dataset.

Use the final Barchart continuous series and restrict the input to the chosen 6-month period in a reproducible way. The research-run archive must exist before this run is considered an official Phase 12 baseline.

Record at minimum:

- exact source file and SHA-256
- selected date range
- rows used
- contracts traversed
- rollover audit reference
- Git SHA
- strategy/session config snapshots
- trade ledger
- metrics JSON
- pipeline audit
- warnings/degraded state

No strategy tuning before this run.

---

# Stage C — 12-month untouched Barchart baseline

## Goal

Establish the primary annual-scale baseline before any formal parameter calibration.

Requirements:

- same baseline strategy/config as the 6-month run
- validated rollover boundaries
- no price back-adjustment
- exact source/contract metadata preserved
- duplicate/gap diagnostics reviewed
- complete archived run bundle

Do not use the 12-month sample as both the repeatedly tuned training set and final proof.

---

# Stage D — Year-by-year and full-history baselines

## Goal

Measure whether strategy behavior is stable across changing volatility and market regimes.

Run each available calendar year / major annual window separately, then run the entire certified multi-year sample. Preserve every run independently.

Year-by-year comparison is required before interpreting full-history aggregate profitability as robust.

---

# Metrics to capture for every horizon

Minimum headline metrics:

- number of trades
- win rate
- average and median R
- expectancy in points
- expectancy in R
- profit factor
- TP1 / TP2 / TP3 / TP4 hit rates
- stop rate
- no-trade rate where applicable
- MFE
- MAE
- maximum adverse streak
- maximum drawdown if supported
- average hold time
- net points / R

Required segmentation:

- direction: long / short
- setup family: reversal / continuation
- score band
- DOL classification/alignment
- bias state
- session context
- volatility regime
- month / year / contract
- displacement present/absent
- structure shift present/absent
- FVG context present/absent
- liquidity-sweep context
- entry reason
- exit reason

A higher score band should outperform lower score bands over a meaningful sample before score thresholds are treated as calibrated.

---

# Calibration workflow

Do not optimize all parameters at once.

Recommended order:

1. Validate data and rollover correctness — now substantially complete for the certified Barchart series.
2. Implement automatic research-run archiving.
3. Validate trade-generation logic through individual ledger inspection.
4. Establish 6-month, 12-month, year-by-year, and full-history untouched baselines.
5. Perform segmentation analysis.
6. Identify one hypothesis for improvement.
7. Change one parameter family at a time.
8. Re-run the same training sample.
9. Reject changes that only improve a narrow period/regime.
10. Validate accepted candidates on held-out / walk-forward periods.
11. Compare historical behavior to Phase 11 shadow-mode observations.
12. Only then update production strategy configuration.

Parameters listed in `phases.md` for calibration include displacement thresholds, SNR thresholds/weights, support/resistance confluence weights, scorer weights, confidence bands, DOL thresholds/weights, swing parameters, FVG significance, RVOL thresholds, stop buffers, room-to-run filters, exit model, and target priorities.

---

# Walk-forward / out-of-sample rule

The annual and multi-year datasets must not be repeatedly tuned and then used as their own proof.

At minimum:

- earlier portion = development/calibration
- later untouched portion = validation

Prefer rolling walk-forward windows once candidate improvements exist so parameters are evaluated across multiple unseen periods.

Never choose parameters solely because they maximize historical net profit.

---

# Automatic research-run archive requirement

Before the next official large baseline, implement an archiver so `run_pipeline.py` can continue writing compatibility outputs such as:

```text
data/results/backtest/trades.csv
data/results/backtest/backtest_metrics.json
data/results/pipeline/latest_run.json
```

while every meaningful research run is also preserved under a unique directory such as:

```text
data/results/research_runs/
  2026-09-05_6m_baseline_<run-id>/
  2026-09-05_12m_baseline_<run-id>/
  2026-09-05_2025_baseline_<run-id>/
  2026-09-05_full_history_baseline_<run-id>/
```

Each run archive must contain or reference:

- run timestamp / unique run ID
- input path
- input SHA-256
- source
- selected date range
- row count
- contract list
- rollover audit path/hash or immutable reference
- Git commit SHA
- strategy config snapshot
- sessions config snapshot
- trade ledger
- metrics JSON
- pipeline audit
- warnings/degraded-analysis state
- optional human notes / experiment hypothesis

Research-run contents remain outside Git because they can be large. The code, archive format, and documentation belong in Git.

---

# Phase 12 completion gates

Phase 12 is not complete merely because the pipeline can produce a profitable backtest.

Required before completion:

- [x] multi-year explicit-contract historical source acquired
- [x] normalized chunk-level Barchart data audited
- [x] 19 quarterly contract Parquets built and audited
- [x] 18 rollover boundaries validated by confirmed volume crossover
- [x] continuous non-back-adjusted MNQ series created and audited
- [ ] automatic research-run archiver implemented and tested
- [ ] untouched 6-month baseline archived
- [ ] untouched 12-month baseline archived
- [ ] year-by-year baselines archived and compared
- [ ] full certified multi-year baseline archived
- [ ] sufficient trade sample analyzed with required segmentation
- [ ] exit-model experiments completed as controlled experiments
- [ ] score bands checked for monotonic usefulness
- [ ] walk-forward or held-out evaluation completed
- [ ] historical results compared against Phase 11 shadow-mode observations
- [ ] accepted parameter changes shown stable across regimes
- [ ] final configs and evidence committed/documented
- [ ] `phases.md` updated with final Phase 12 completion evidence

---

# Historical-source note

ProjectX remains the live/production market-data source. Barchart is the research source for expired-contract multi-year MNQ history because the current ProjectX account/API path did not expose usable historical bars for the required expired contracts.

See `docs/BARCHART_HISTORY_WORKFLOW.md` for acquisition, normalization, contract-building, rollover, and stitching evidence.
