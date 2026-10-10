# NQ Automated Strategy (Pine v6) — separate track

**Status:** specification only. No live execution or even simulated orders have been implemented here yet.

This folder will contain one or more versioned Pine v6 files using strategy() and actual strategy.entry()/strategy.exit() calls, separate from the chart indicator. The strategy should be derived from the established Python setup-family and market-execution contracts, not from the uploaded legacy Context8 indicator's overly restrictive conditions.

## Confirmed research inputs
- 09:30–10:30 America/New_York for new entries.
- Breakout / confirmed retest and liquidity-sweep / reversal models remain separately testable.
- Previous RTH high/low; premarket 04:00–09:30; London 02:00–05:00.
- Use confirmed swings, FVG, structure, displacement, market-quality SNR and DOL with Python-equivalent definitions.
- Python-configured preferred structural stop range is 20–25 NQ points, structural buffer 2 points. Research variants may test 15–35.
- TP milestones: +25, +50, +75 and +100 points. They are milestones, not necessarily partial orders.
- Current Python trade_management defaults: no partial exits and no initial move to breakeven.
- One open trade maximum; entry after confirmed retest; conservative stop-first same-bar collision; account costs/slippage explicitly modeled.
- A raw 0–100 research score is **not** a win probability.

## Before writing strategy() logic
1. Inspect the complete Python setup-family, planner and backtest execution semantics and their tests.
2. Lock the experiment specification and specify any deliberately reduced Pine baseline.
3. Verify same-bar fills, next-bar entry, stop/TP sequencing, trade expiry, overnight gaps and contract rollover assumptions.
4. Cross-check signals against Python on controlled bar fixtures, including negative/rejected setups.
5. Run TradingView Premium Deep Backtesting in development/validation/holdout periods without optimizing the holdout.
6. Only then plan paper order routing; live routing requires independent risk gateway, position reconciliation, kill switch, supported broker/prop firm API and approval.

The chart **indicator** remains in ../indicators/. Webhook **research snapshots** are not broker order requests.
