# MSS/FVG raw-event parity audit — read-only

Branch: **feature/tradingview-pinescript**.
Tool: [compare_mss_fvg.py](compare_mss_fvg.py).
Tests: [test_compare_mss_fvg.py](../tests/test_compare_mss_fvg.py).

## Purpose and scope

Investigate whether the V2 2/2-pivot **MSS proxy** and three-candle
**FVG creation** differ from canonical Python, using exactly aligned
one-minute MNQ bars.

The script reuses unchanged canonical Python functions from:
- src/swings.py: causal swings and last two confirmed extrema
- src/structure.py: internal trend, buffered close-break,
  level deduplication and BOS/MSS classification
- src/fvg.py: raw three-candle gap creation

Settings come from main config/strategy.yaml. No existing strategies,
research pipeline, EXP-030, or R7–R12 contracts are modified.

**Explicit limitations:** raw events only, not full staged linked entry
candidates, object-based FVG retest/IFVG lifecycle, confluence or fills.
Pine MSS is a proxy; an event mismatch is a research finding, not automatic
proof of a coding error or a reason to relax trading rules.

## Export input once (not a trade list)

1. Load **MNQ V2 Diagnostics** on TradingView's 1-minute MNQ chart.
2. Choose **Export chart data** (OHLC + indicator Data Window plots), NOT
   Strategy Report's trade list CSV.
3. The chart CSV must have time, open, high, low, close and the four plots
   named Bullish MSS proxy, Bearish MSS proxy, Bullish FVG created,
   Bearish FVG created. Unique script-name prefixes are supported.
4. Record the chart contract and feed, continuous roll-adjustment setting,
   and relevant chart window. Chart-loaded bars and Deep Backtesting date
   range are different populations. We will not call an October
   chart-data audit a January–June 2025 backtest audit.

## Run from repo root in the existing Python venv

~~~bash
python tradingview/audit/compare_mss_fvg.py \
  --pine-chart /path/to/tradingview-chart-data.csv \
  --output /tmp/mnq_mss_fvg_audit.json
~~~

The default mode applies the canonical Python implementation to the SAME
TradingView OHLC bars; it isolates event-definition differences without
bringing in a separate price-data source. This is not independent market
data validation.

A separate raw-data/roll-parity pass is available for an independently
sourced full-history MNQ one-minute parquet or CSV:

~~~bash
python tradingview/audit/compare_mss_fvg.py \
  --pine-chart /path/to/tradingview-chart-data.csv \
  --reference-bars /path/to/MNQ_1m_normalized.parquet \
  --output /tmp/mnq_independent_source_audit.json
~~~

The independent-source mode requires overlapping open/high/low/close prices
to agree within 0.125 Nasdaq index points (half a tick). If not, the
auditor REFUSES to draw event-comparison conclusions: investigate contract
roll, back-adjustment and timestamp conventions first.

UTC-aware timestamp values only: ISO-8601 with a numeric offset or UNIX
epoch seconds/milliseconds. No guessed timezone or daylight-saving offset.
Candle timestamps must represent their **opening minute**, and duplicated
timestamps are not accepted. A 40-shared-bar warmup exclusion is the
default, with at least 100 subsequent comparable bars required; options
--warmup-bars and --min-shared-bars control these gates.

Outputs contain per-signal Pine/Python counts, exact overlap, Pine-only
and Python-only events, and first mismatch timestamps in UTC.

Exit status: 0 = raw event agreement; 1 = one or more differences;
2 = cannot compare safely. A matching raw event report does NOT establish
ordered setup parity or profitable live execution.

## Local and isolated GitHub tests

~~~bash
python -m pytest tradingview/tests/test_v2_diagnostics_source_parity.py \
  tradingview/tests/test_compare_mss_fvg.py -q
~~~

These tests do not compile Pine or connect to the user's VPS. No execution
or backtest result should be claimed until tests complete.

## Acceptance gates

- [ ] Run the isolated regression suite.
- [ ] Get at least one usable one-minute chart data export; confirm OHLC
      and four raw indicator series, with ample historical warmup.
- [ ] Compare with canonical Python on the exact same candles.
- [ ] Classify MSS mismatches by pivot tie, active-level deduplication,
      and bullish/bearish trend state; classify FVG gaps by bounds.
- [ ] If comparing to independent Barchart history, resolve roll/price
      mismatches before investigating indicator logic.
- [ ] Then investigate full FVG retest/hold sequence and entry-window
      eligibility in a separate preregistered research candidate.
- [ ] Keep 2025 H2 holdout untouched during iteration.
