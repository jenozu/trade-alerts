# TradingView / Pine Script v6 — Indicator and strategy tracks

Branch: feature/tradingview-pinescript. Existing Python research on main remains source of truth; do not alter EXP-030, R7–R12, strategy config, session config or active research runs without explicit separate authorization.

## Pine 1 — Market Intelligence Indicator
**Current:** [indicators/nq_market_intelligence_v1.pine](indicators/nq_market_intelligence_v1.pine). Added to TradingView on a **1-minute** chart by the user and visually loaded without a runtime error. This confirms basic chart loading, **not** quantitative parity with Python.

- PDH/PDL, PMH/PML, London 02–05 ET, Asia/overnight, OR5/OR15 and chart context.
- EMA 9/21, optional VWAP, non-directional SNR quality, rolling RVOL, FVG/swing/sweep research markers.
- Optional JSON research snapshots: Off by default. No webhook receiver or VPS endpoint deployed.
- 15m/30m/1h confirmed-bar EMA proxies do NOT equal full Python structural HTF bias.
- No live trades; no simulated strategy.entry()/strategy.exit().

See [docs/indicator_v1_review.md](docs/indicator_v1_review.md).

## Pine 2 — Automated Strategy / Deep Backtesting
**Breakout V1:** [strategies/nq_breakout_retest_v1.pine](strategies/nq_breakout_retest_v1.pine), a simulation-only baseline. User verified Strategy Tester generated 14 trades Sep–Oct 2026 (net −$105 with zero commissions, win rate 28.57%, profit factor 0.792); this is *not* a conclusion about the full strategy.

**Reversal V2:** [strategies/nq_sweep_reversal_v2_research.pine](strategies/nq_sweep_reversal_v2_research.pine), a separate ordered sweep → displacement → MSS proxy → FVG → retest research strategy; code committed, Pine compilation/backtesting not yet verified. [Reversal protocol](backtests/reversal_v2_protocol.md).

- Primary PMH/PML 04:00–09:30 ET, or optional previous completed RTH PDH/PDL.
- Close-confirmed breakout → later retest touch and hold → next 1m open market fill, strict 09:30–10:30 entry window.
- One open position, fixed 25-point default stop, single selected TP milestone (25/50/75/100), 60-minute max hold. No partial exits/breakeven.
- Deliberately does NOT claim full Python strategy parity, calibrated scoring, liquidity sweep reversal support, or live broker execution.
- See [strategies/README.md](strategies/README.md) and [backtests/strategy_v1_protocol.md](backtests/strategy_v1_protocol.md) for test plan and limitations.

## Remaining directories
- [alerts/](alerts/): research JSON telemetry contract; no VPS receiver active.
- [configs/](configs/): Python/Pine parity definitions and differences.
- [docs/](docs/): TradingView manual setup, indicators and validation.
- [backtests/](backtests/): test protocol, future versioned reports (no copyrighted market data in Git).

## Immediate next action
Compile the new **strategy** on TradingView Premium; check that simulated trades appear in Strategy Tester; then verify a sample and begin versioned Deep Backtesting. Do not expand the indicator dashboard, design the VPS receiver or connect a live broker until the backtesting baseline is verified.

## Boundaries
- Session times are America/New_York with daylight savings.
- Market-quality SNR must NEVER silently become support/resistance or a bullish/bearish predictor.
- Raw 0–100 confluence score is not a calibrated win probability.
- Record exact symbol/contract/roll settings, tester costs, fills and strategies for repeatability; differences with Python must be documented.
- No production claims from uncompiled Pine source or from profitable in-sample trade summaries.
- Do not commit secrets, live account identifiers or paid/raw market datasets.

No changes were made to main, EXP-030, R7–R12 or existing Python strategy configurations for these TradingView commits.
