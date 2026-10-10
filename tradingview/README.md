# TradingView / Pine Script v6 — indicator and strategy tracks

Branch: feature/tradingview-pinescript | Python research source of truth: main.
Do not modify EXP-030, R7–R12 objectives, the active experiment request, or the active Python configuration from this branch.

## Separate components

### Pine Script 1: NQ Market Intelligence Indicator — **V1 committed, TradingView verification pending**
File: indicators/nq_market_intelligence_v1.pine

- Chart context: PDH/PDL (previous RTH), premarket 04:00–09:30, London 02:00–05:00, Asia, overnight, OR5/OR15, VWAP, EMA9/21.
- Research diagnostics: non-directional SNR quality, relative volume, causal confirmed swing breaks, simple FVG/hold/invalidation zones, reference liquidity sweeps.
- Optional 1m/5m confirmed-bar JSON research snapshots via TradingView alert() (Off by default). Alerts do not place trades.
- The 15m/30m/1H EMA context shown is a **proxy only**, not the Python structural HTF bias.
- No entry, SL, TP, trade instructions, broker orders or simulated strategy trades; those require validated rules.

See docs/indicator_v1_review.md for exact caveats and chart-side tests.

### Pine Script 2: NQ Automated Strategy — **specification only**
Folder: strategies/

- Later use strategy() plus strategy.entry()/strategy.exit() for executable simulation in TradingView Premium Strategy Tester / Deep Backtesting.
- Historical-only baseline first: breakout/retest and sweep/reversal are distinct models, tested against current Python setup-family and trade-planner contracts.
- 09:30–10:30 ET entry window, 20–25 point preferred structural risk, milestone TP1 +25, TP2 +50, TP3 +75, TP4 +100.
- Production automation requires out-of-sample + paper verification and a separate risk-controlled broker gateway. No live routing before that.

See strategies/README.md.

### Other folders
- alerts/: research snapshot schema / eventual receiver contract; no VPS receiver deployed.
- backtests/: experiment manifests and Deep Backtesting interpretation (not paid/raw market datasets).
- configs/: Python/Pine parity matrix and config mismatch tracking.
- docs/: chart instructions, verification records, review decisions.

## Development order
1. Load Indicator V1 into TradingView Premium on a **1-minute** MNQ/NQ futures chart and resolve any Pine compiler/UI errors. No compile claim until manually verified in TradingView.
2. Compare several dated level calculations and reference signals with Python (DST, session overlap, FVG age, sweep conditions). Reconcile VWAP reset disagreement between strategy.yaml and sessions.yaml before parity approval.
3. Incrementally add authentic Python market-state concepts and later research-qualified ENTRY/SL/TP overlays, preserving the old indicator's desired chart layout without importing its invalid trading logic.
4. Implement separate Pine strategy baseline, compare trades with Python, test Deep Backtesting using in-sample/validation/untouched holdout data, costs and Bar Magnifier assumptions.
5. Build VPS webhook ingestion with authenticity checks, deduplication and outage recovery; this is telemetry only.
6. Paper trading and eventually permitted brokerage execution via a separate safety gateway after explicit approval.

## Important safeguards
- Python feature semantics and current research definitions remain authoritative.
- Only completed candles and causally available higher-timeframe information may determine confirmed events.
- SNR = market quality, not bullish/bearish bias or win probability.
- No look-ahead, DST mistakes, inconsistent contract rollover, or silent proxy substitutions.
- Store strategy version, symbol/contract, settings, test dates, costs and exports for reproducibility.
- No credentials, account IDs, raw licensed data or private exports in Git.
- All the current work is isolated to feature/tradingview-pinescript; main and EXP-030 are untouched.

**Current checkpoint:** Indicator V1 committed; separate strategy/telemetry specifications committed; no TradingView compilation, Python tests, deep backtests or live alerts run for this checkpoint.
