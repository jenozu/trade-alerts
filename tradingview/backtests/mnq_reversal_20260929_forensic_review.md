# MNQ reversal V2 — first-trade forensic review

Status: **PENDING MARKET DATA** (as of 2026-10-10). This is a source/assumption audit, **not** a validated Python/Pine parity finding or a profitability conclusion.

## Evidence already observed

- A screenshot of the reloaded **MNQ REV v2** TradingView Strategy Report for September 20–October 9, 2026 shows **one winner, +$100 simulated**, zero commissions, one fixed MNQ contract. This is consistent with a 50-index-point full-target fill at $2 per index point.
- A separate *earlier NQ* strategy trade-list screenshot shows a Sep 29 2026 short, entry **09:38 at 30,610.75**, exit **09:42 at 30,560.75**, for a 50-point gross move and **$1,000 NQ-sized result**. **Do not silently equate these timestamps/fill prices with the corrected MNQ strategy** until the MNQ trade list is checked.
- The latest V2 Pine code enforces `syminfo.root == "MNQ"` and `syminfo.pointvalue == 2.0`. Source: ../strategies/nq_sweep_reversal_v2_research.pine. The user's saved TradingView copy is separate from GitHub and must be checked for revision parity.
- Existing results are from the current small chart-tested interval, not a complete Deep Backtesting period; commissions are zero; Bar Magnifier status and rollover settings are unknown.

## Source-review findings before trade analysis

The Pine strategy has an ordered state machine for:
1. Known buy-side liquidity-level sweep (short) or sell-side sweep (long), one tick penetration then close back.
2. Directional displacement measured against a 14-period SMA true-range and prior-20-bar median body.
3. An **MSS proxy**, requiring a countertrend relationship of confirmed 2/2 pivots and a one-tick close break.
4. A tracked 1-minute FVG created after MSS.
5. A later-bar touch/hold of that FVG, placing a strategy market entry for the next minute's open if the entry window permits.

**Parity caveats:** Pine sweep additionally requires the previous candle's high/low on the near side of the level; Python has a broader registry and deduplicated sweep object semantics. Pine trend/MSS and single-FVG tracking do not prove equivalence to Python's causal swing/structure and linked `fvg_chronology_v2`. Pine uses a fixed 25-point stop and one terminal TP2 of 50 points; Python's structural-stop/TP4 control and conservative same-bar stop-first execution differ. Event flags should be checked before interpreting trade counts as effects of market regime/filters.

## Input needed — one TradingView chart CSV

Use **MNQ1! / CME_MINI** on **1-minute chart**, with the latest **MNQ REV v2** strategy enabled. Load **at least 2026-09-28 09:30 ET through 2026-09-29 09:45 ET** on the chart by scrolling back as needed (Sep 28 previous RTH needed for PDH/PDL; Sep 29 London/PM for high/low; longer history is fine).

In TradingView's top toolbar choose **Download chart data…**, choose the active MNQ chart, download CSV, and upload the CSV to the ChatGPT conversation. The export covers **loaded chart data**, not guaranteed full history; check first and last CSV timestamps. TradingView documentation says indicator/strategy numeric plot series shown only in Data Window are exportable. See:
- https://www.tradingview.com/support/solutions/43000537255-how-to-export-chart-data/
- https://www.tradingview.com/pine-script-docs/faq/indicators/

Useful columns: time (UTC or offset-aware), open, high, low, close, volume, **Short reversal stage 0-4**, **Buy-side sweep candidate**, **Bearish displacement candidate**, **Bearish MSS proxy**, **Bearish FVG created**, **Confirmed reversal short**. Similar long-series columns are useful for false-positive checks. TradingView may prefix headers with script labels.

Optionally export the **MNQ** (not earlier NQ) strategy trade list as CSV, if available, to confirm exact fills; otherwise the trade-list screenshot suffices.

## Validation procedure once files arrive

1. Parse timestamps as exchange/chart timestamps, convert to America/New_York; reject ambiguous naive times without an explicit timezone assumption.
2. Verify source symbol/contract, 1-minute regularity, loaded-chart data range, rollover/back-adjustment and dataset completeness; missing periods **block** a claim about session levels.
3. Recalculate previous completed RTH PDH/PDL, Sep 29 premarket 04:00–09:30 PMH/PML, London 02:00–05:00 LOH/LOL, using only bars available when the signal was generated.
4. List Pine diagnostic columns and event timestamps in a 09:20–09:45 ET timeline; follow the exact state changes and confirm that direction, sweep, displacement, MSS proxy, FVG creation, FVG hold and confirmation occur in order. Inspect prior minutes if first event predates 09:20.
5. Check that the signal was finalized at an actual completed candle and the following **real** one-minute bar opened before 10:30 ET.
6. Compare MNQ simulator entry, stop and TP to OHLC path; flag candles touching both stop and target (simulator fill ordering is not automatically the Python stop-first rule).
7. Independently calculate/compare Python sweep/displacement/structure/FVG flags on the same **MNQ** feed (with explicit missing-data and contract mismatches). Report discrepancies rather than tuning the rules to force a profitable trade.
8. Record a verdict: **VALIDATED SEQUENCE**, **IMPLEMENTATION MISMATCH**, or **INSUFFICIENT DATA**. A valid sequence still does *not* imply a profitable strategy.

Do not modify the active Python research pipeline, the EXP-030 experiment, the historic controls or the untouched holdout periods merely to fit this trade.
