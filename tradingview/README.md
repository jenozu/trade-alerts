# TradingView / Pine Script Research Workspace

Development branch: `feature/tradingview-pinescript`.
This is an isolated, research-only companion to the existing Python engine.
Do not change `config/strategy.yaml`, `config/sessions.yaml`, EXP-030, R7–R12, or active run requests from this workspace.

## Source-of-truth and scope
- Python feature semantics and existing strategy configuration are authoritative until a reviewed parity comparison explicitly approves a difference.
- Pine v6 strategies are for TradingView Premium Strategy Tester / Deep Backtesting experiments.
- No live orders, broker integrations, or webhook-based order execution in the initial milestone.
- Treat each proposed SMC filter as a hypothesis, not a guaranteed improvement.
- Never interpret the 0–100 raw confluence score as a win probability.

## Repository map
- `strategies/`: Pine v6 backtesting strategies (after rule translation and parity review)
- `indicators/`: optional chart overlays and debug series
- `alerts/`: versioned webhook event schemas (research telemetry only)
- `backtests/`: experiment manifests and result interpretation, not raw/private datasets
- `configs/`: Pine-to-Python rule crosswalks
- `docs/`: verification checklists and TradingView manual setup

## Milestones
1. Inventory exact Python entry/exit semantics and current experiment constraints.
2. Implement minimum measurable breakout/retest strategy in Pine v6; label any simplification.
3. Cross-check sample bars, session levels, candidate signals and fills against Python.
4. Run Premium Deep Backtesting with defined date range, fees, slippage, contract and bar magnifier assumptions.
5. Export and record strategy results and compare untouched holdout periods.
6. Only later add realtime webhook telemetry, fail-safe collection and supported paper execution.

## Invariants
- Exchange futures symbols/contracts, timezone, RTH versus Globex levels and roll adjustments must be explicit.
- Trading session is America/New_York; entries only from 09:30 to 10:30.
- Confirmed bars only; higher timeframe values must not leak future candles.
- Ambiguous TP/SL sequencing must be handled conservatively and reported.
- Keep strategy code, configuration, exact dataset, commission/slippage, run date and screenshots/exports paired for repeatability.
- Avoid committing account identifiers, tokens, raw paid market datasets, or private exports.

Current status: branch and documentation scaffold only; no Pine strategy has been validated.
