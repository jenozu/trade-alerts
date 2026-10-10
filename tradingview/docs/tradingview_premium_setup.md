# TradingView Premium development setup

1. Open a chart for the exact traded NQ/MNQ futures contract and record the contract symbol, exchange, feed, adjusted/continuous setting and timezone.
2. Use a 1-minute chart for the initial research pass. Verify sufficient chart/history data exists for the intended period.
3. After the first Pine v6 `strategy()` is committed and reviewed, open Pine Editor, paste its source, save it and select Add to Chart.
4. Open Strategy Tester; use Deep Backtesting to select the historical date range supported for this instrument. Record the start/end dates and available sample size.
5. Set position size, contract multiplier, commission and slippage explicitly. Enable Bar Magnifier when available; note historical fill limitations.
6. Export Strategy Report/trades where supported, retain the strategy version and exact input settings, and compare outcomes to Python using matching assumptions.
7. Do not create live trade alerts or connect to a broker until parity, out-of-sample testing and paper execution have passed their respective gates.

## Immediate next development step
Read the rest of `config/strategy.yaml`, `src/backtest.py`, the setup-family contract, trade planner and existing tests to reconstruct the **current** strategy's entry, retest confirmation, stop and target decisions. Then implement the smallest measurable Pine baseline without changing the Python research program.
