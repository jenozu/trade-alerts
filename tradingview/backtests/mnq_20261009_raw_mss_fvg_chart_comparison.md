# MNQ1! Oct 9 2026 — raw MSS/FVG chart-data comparison

**Recorded:** 2026-10-11
**Source:** user-uploaded TradingView `Download chart data` CSV, chart `CME_MINI:MNQ1!`, timeframe **1 minute**, Unix timestamps in UTC.
**Uploaded CSV SHA-256:** `473705df592c49751bf0c4b9d6cc95c6470ddfeacbe1a39bb79492cc51a6fec4`. The user's raw market data are **not committed**.
**Date coverage:** 2026-10-09 **16:00–20:59 UTC**, equivalent to **12:00–16:59 America/New_York (EDT)**, precisely 300 consecutive one-minute candles. No 09:30–10:30 ET entry-window bars are present.

## Preliminary candle-by-candle result

The comparison used the four unambiguous diagnostic fields
`Bullish MSS proxy`, `Bearish MSS proxy`, `Bullish FVG created`,
`Bearish FVG created`. The export contains **181 columns** because
multiple strategies/indicators were loaded, including repeated numbered
copies of these fields. All four repeated copies of each field matched
the primary field across all 300 rows.

We excluded the first **40 candles** (partial-history pivot/structure and
3-candle FVG warmup) before comparing **260 one-minute bars**, from **12:40 to
16:59 ET**. FVG candidates appearing in the first exported rows can depend
on candles not present in the export and are **not comparable**.

| Raw event flag | TradingView Pine | Python-rule reconstruction | Identical events | Pine only | Python only |
| --- | ---: | ---: | ---: | ---: | ---: |
| Bullish MSS | 2 | 2 | 2 | 0 | 0 |
| Bearish MSS | 5 | 5 | 5 | 0 | 0 |
| Bullish FVG creation | 31 | 31 | 31 | 0 | 0 |
| Bearish FVG creation | 24 | 24 | 24 | 0 | 0 |

**Interpretation:** No raw-event disagreement was detected **on this one
afternoon sample**. This is NOT proof of all-date parity, and not evidence
that 2025 backtesting entries are identical to Python production entries.

### Methodological qualification

The local comparison **reconstructed** the relevant canonical Python
algorithms from the source on `main`, rather than executing the GitHub
repository's original Python modules directly:

- `src/swings.py`: internal pivots with strict comparison on two left bars,
  non-strict comparison on two right bars, event emitted at right-bar close.
- `src/structure.py`: internal trend from last two confirmed swing highs
  and lows; first break deduplicated by active swing price; strict
  close-through-level with the configured **0.25-point buffer**; classify
  bullish/bearish MSS only for countertrend structure break.
- `src/fvg.py`: three-candle gap with **minimum one 0.25-point tick**,
  no ATR fraction filter and no per-candle displacement requirement.

The script `tradingview/audit/compare_mss_fvg.py` was separately committed
to call the actual canonical modules. **It has not yet been run successfully
against this CSV on the repository environment**, so do not upgrade this
preliminary comparison to direct execution parity.

### Chart state and selection caveats

Across all 300 exported candles, there were:
- 3 raw bullish MSS proxy flags and 5 bearish MSS proxy flags (one bullish
  event occurred in the 40-bar warmup).
- 37 raw bullish FVG creation flags and 30 bearish FVG creation flags.
- **Zero** sell-side sweep candidates and **zero** buy-side sweep candidates.
- **Zero** active reversal-stage bars or confirmed reversal entry signals.

The screenshot's prior dashboard totals (151 sweeps, 58 displacement-stage
completions, 11 MSS-stage completions, 9 linked FVGs, one entry) were
calculated over a **different set of loaded chart candles**. They must
not be equated with the 300-row export or with the 2025-H1 Deep Backtest.

A raw FVG creation count is **not** the number of linked FVG stages,
and a raw MSS proxy event is **not** an ordered post-sweep MSS stage.
The lack of stage events in this afternoon-only extract says nothing
about valid morning-entry frequency.

## Controlled next research step

1. Obtain TradingView **chart data** covering a morning session with warmup,
   preferably **09:00–11:00 ET** plus prior history (at least 40 1-minute
   bars before the comparison period); target a known example such as
   September 29, 2026, subject to chart export availability.
2. Run `tradingview/audit/compare_mss_fvg.py` against that chart CSV
   within the repository checkout, with the canonical modules imported,
   and record first timestamp-specific divergences.
3. Compare the **ordered** sweep → displacement → MSS → linked FVG → hold →
   next-open gate against actual Python candidate contracts; examine
   09:30–10:30 ET and out-of-window rejections.
4. Do not alter V2 thresholds, stop, targets, or the protected 2025-H2
   holdout in response to a single afternoon sample.

**Research status:** Preliminary raw-event match on a restricted sample.
Production Python parity and causal order validation remain pending.
