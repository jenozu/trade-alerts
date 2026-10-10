# Pine Script 2 — NQ Automated Trading Strategy (research)

**V1 code:** [nq_breakout_retest_v1.pine](nq_breakout_retest_v1.pine)
**V1 protocol:** [Deep Backtesting / acceptance](../backtests/strategy_v1_protocol.md)
**Status:** Version 1 Pine code committed; **TradingView compile, historical fills and Python trade parity pending**. No live orders or broker webhooks.

## Current deliverable: breakout/retest baseline only
- Pine v6 strategy() (NOT an indicator) submits *simulated* market orders after an independent confirmed-breakout and later confirmed retest.
- New entries only when next 1-minute open will be within 09:30–10:30 ET.
- Select PMH/PML (04:00–09:30 ET) or PDH/PDL (previous RTH 09:30–16:00 ET).
- One open trade maximum; stops and targets attached using tick-relative strategy.exit().
- Configurable fixed 25-point default stop; +25/+50/+75/+100 milestones selectable as a **single terminal full-position TP**; no initial partials or breakeven.
- Max hold 60 1-minute bars; 1-tick simulated slippage; **zero default commission must be replaced by realistic fee assumptions**; 5% *illustrative* futures simulator margin.
- Minimal chart decoration; results live in Strategy Tester.

**Deliberate non-parity:** This simple baseline does **not** reproduce full Python structural stops, original linked setup family/confirmation events, 0–100 score, FVG/IFVG, BOS/MSS, DOL, Python SNR, live order or conservative same-bar stop-first simulation. It must never be described as the finished bot or proven profitable. The Python code and EXP-030/R7–R12 remain untouched.

## Next gated tasks
1. Compile the script in TradingView on an NQ/MNQ **1-minute** chart; address all compiler/runtime errors.
2. Run a short chart-level sample, inspect breakout/retest timestamps, next-open fills, stops/targets, forced expiry and false signals.
3. Compare a sample of events with existing Python canonical session levels and entry timings, explicitly list differences.
4. Run a versioned TradingView Premium Deep Backtesting baseline, setting realistic commissions/slippage and a data-dependent Bar Magnifier policy.
5. Evaluate separate independent improvements (reversal family, SNR market-quality gate, HTF, DOL, structural stop) without optimizing an untouched holdout.
6. Plan research telemetry and **paper** execution independently; live automation requires an approved broker integration, independent risk controls, a kill switch and forward validation.

Our chart **Market Intelligence Indicator** is separately stored under [../indicators](../indicators). That indicator contains no trading orders. Live telemetry plans are in [../alerts](../alerts).
