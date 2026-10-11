# MVP audit — September 29, 2026 MNQ morning reversal (chart export)

**Date inspected:** 2026-10-11.
**Source:** user-uploaded TradingView **Export chart data** CSV, chart `CME_MINI:MNQ1!` 1 minute, UTC Unix bar-*opening* timestamps, with MNQ V2 diagnostic indicator series. This CSV contains chart/indicator data, **not a trade ledger or independently sourced Barchart candles**. User-chosen filename is not authoritative for Pine script identity.
**File SHA-256:** `e4d3db1fa2e86ba62a9f0f540cfde228da485c7f5ff0c84372082fb1cea8c95c`. Raw CSV not committed.
**Rows:** 11,578 x 53 columns. Coverage begins 2026-09-29 **08:02 ET** and ends 2026-10-09 **16:59 ET**; includes normal futures maintenance/weekend gaps. First 40 rows excluded from cross-code signal checks for partial-history warmup.

## VPS direct-import audit — verified 2026-10-11

The user ran the **actual existing canonical Python modules** through
`tradingview/audit/compare_mss_fvg.py` from the isolated
`/docker/trade-alerts-tv-audit` checkout (not by changing `main`).
The same TradingView chart CSV was uploaded separately to
`/root/mnq_sep29_chart.csv` on their VPS.

- Targeted regression suite: **11 passed in 2.11 seconds**.
- Audit completed, **11,578 chart bars / 11,538 compared** after 40 warmup
  bars; actual data source was **TradingView OHLC**, not Barchart.
- Exact paired results:

| Signal | Pine | Canonical Python | Both | Pine only | Python only | Disagreeing bars |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Bullish MSS | 143 | 133 | 120 | 23 | 13 | 36 |
| Bearish MSS | 151 | 139 | 130 | 21 | 9 | 30 |
| Bullish FVG created | 1,168 | 1,168 | 1,168 | 0 | 0 | **0** |
| Bearish FVG created | 1,136 | 1,136 | 1,136 | 0 | 0 | **0** |

- Audit status was `differences_found`, exit **1**, which is the
  documented **valid difference-reporting outcome**, not a crash or failed
  test.
- The first UTC timestamp with an MSS difference was
  **2026-09-29 14:54 UTC = 10:54 ET**, after the 09:30–10:30 entry window.
- The direct-import audit's **global aggregates** matched the earlier
  reconstruction's aggregates exactly, strengthening confidence in that
  earlier exploratory analysis. However, the terminal's 20 printed
  mismatch examples are **not** a complete timestamped concordance:
  claiming canonical **morning-only** or **active-stage** zero differences
  still requires computing those specific intersections with canonical
  events. The reconstruction's morning/stage classifications below remain
  *source-guided* until then.
- **MVP disposition:** raw FVG calculation parity is confirmed on this
  sample; Python and Pine raw MSS semantics are **not identical** and
  that difference is acknowledged. No evidence yet that a mismatch
  affects the one observed 09:37 ET V2 short entry, and no justification
  yet to rewrite entry criteria or re-optimize parameters.

This validates **raw-event implementation only**, not the seven-step
order workflow, source-independent market-data integrity, complete
Barchart/continuous-contract history, or profitability.

## September 29 qualifying short — observed in exported Pine flags

| Candle opening time (America/New_York) | Observation |
| --- | --- |
| **09:30** | `Buy-side sweep candidate=1`; short setup state goes **0 -> 1**. This same bar has raw bearish displacement, but the baseline only accepts displacement **after** sweep bar. |
| **09:33** | `Bearish displacement candidate=1` AND `Bearish MSS proxy=1`; short setup advances **1 -> 2 -> 3** within this bar. |
| **09:34** | Linked bearish FVG created; short stage **3 -> 4**. Three-candle gap bounded by **30,629.50 (lower)** and **30,652.50 (upper)**. |
| **09:37** | FVG hold after later retest: candle high **30,634.75** enters the gap and close **30,610.50** is below its lower boundary. `Confirmed reversal short=1`; stage resets to 0. |
| **09:38** | Next candle opens at **30,610.50**; strategy order is normally filled next open with broker-emulator slippage. OHLC CSV **does not report broker-emulator executed entry price**. |
| **09:42** | Candle low **30,547.75** crosses the nominal +50-point short target level (subject to simulated fill/fees). Chart OHLC alone does **not** prove exact exit fill or P&L. |

**Critical observation:** This sequence is causally ordered at completed-candle timestamps: sweep, post-sweep displacement & MSS, linked FVG, later retest, next-open intended fill. It does not prove Python's *complete object-linked setup engine* would make the same trade.

### Raw-signal rule-comparison results

A **source-guided reconstruction** of canonical Python `src/swings.py`,
`src/structure.py` and `src/fvg.py` logic was executed against the **same
TradingView OHLC candles** in a local one-off analysis:

- Causal 2/2 swing pivot criteria: high strictly greater than two left
  highs and greater-or-equal to two right highs (and corresponding lows),
  emitting at the pivot's second right-hand confirmation candle;
- Internal trend from last two confirmed swing highs/lows;
- Structure close-break with +/−**0.25-point** buffer, deduplicated until
  the confirmed reference level changes; Python MSS classifies countertrend
  breaks;
- Raw 3-candle FVG of at least one 0.25-point tick, per Python config.

**This was NOT yet direct execution of the actual Python modules on the
repository VPS.** Python raw MSS event semantics are more nuanced than Pine
V2's first-cross MSS *proxy*. Source-level reconstruction can carry defects.

| Comparison population | Bull MSS disagreeing bars | Bear MSS disagreeing bars | Bull FVG disagreeing bars | Bear FVG disagreeing bars |
| --- | ---: | ---: | ---: | ---: |
| **September 29, 09:00–10:30 ET** (91 bars) | 0 | 0 | 0 | 0 |
| **All available 09:30–10:30 ET entry windows** (540 bars over nine trading dates) | 0 | 0 | 0 | 0 |
| **All exported bars after initial 40-bar warmup** (11,538 bars) | **36** | **30** | **0** | **0** |

Full-export post-warmup MSS totals: bullish Pine **143**, reconstructed Python **133**; bearish Pine **151**, Python **139**. This is not proof of defective live signals: some outside-window differences are expected from Python's stateful one-break-per-level deduplication versus Pine's first-cross proxy and potentially different pivot ties. First example: **September 29 10:54 ET**, Pine reports a bullish MSS proxy but the reconstructed Python deduplicated MSS does not. Bar-by-bar classification remains a separate issue; avoid broad rule changes without checking a real entry impact.

**Raw FVG creation** matched at every compared bar: **1,168 bullish and 1,136 bearish** events. A raw gap is not a **linked** post-MSS FVG and does not confirm Python FVG retest/IFVG lifecycle parity.

### Additional diagnostic-only bug found

In the diagnostic Pine source prior to patch, a displacement stage marker
was emitted only when stage advanced **1 -> 2** and stayed at stage 2.
The September 29 **09:33** bar advances **1 -> 2 -> 3**, so the dashboard
omitted its displacement even though the raw displacement flag and the
trading state machine were correct.

Patched `nq_sweep_reversal_v2_diagnostics.pine` to count either resulting
stage **2 or 3**. This is **observational only** and preserves all order rules,
risk settings and the original V2 script. TradingView saved copies are not
auto-synced to GitHub; users need not reload diagnostics unless they want
the revised stage count.

The audit tool `tradingview/audit/compare_mss_fvg.py` also had an output
column-name bug after pandas merge (`name` vs `name_python`), now patched.
A **direct Python-module-backed parity run was later completed on the
user's VPS**, and targeted pytest passed (details above). GitHub Actions
CI itself has not been independently verified.

## Lean follow-up: are out-of-window MSS differences trade-relevant?

On 2026-10-11, the user-provided **11,578-row** chart export was
rechecked locally using the source-guided **Python-rule reconstruction**
(the canonical GitHub modules were not imported or executed in this
isolated runtime).

After excluding the initial 40 warmup bars, MSS proxy vs Python-rule
disagreements total **36 bullish and 30 bearish**. At these 66
timestamp-specific bars:

- **65** were on candles with the same-direction Pine reversal stage **0**
  (no active candidate after processing the bar).
- **One** bullish disagreement at **2026-10-05 05:47 ET** had long
  reversal stage **1**, with `Bullish displacement candidate = 0`,
  `Bullish MSS proxy = 0`, and no entry; it was still awaiting
  displacement, not an eligible MSS-confirmation stage.
- **Zero** disagreed on any stage-2 MSS confirmation in an active
  same-direction setup; **zero** of the disagreement bars had a
  simultaneous corresponding side liquidity sweep flag.
- The early morning mismatches at 2026-10-01 09:14, 2026-10-05 09:06
  and 2026-10-08 09:13 ET all showed **both reversal stages = 0**.
- The confirmed September 29 09:30–09:37 candidate continued
  sweep → displacement/MSS → linked FVG → retest/entry without
  reconstructed raw-event disagreement.

**Provisional MVP decision:** Do **not** rewrite MSS or loosen the
entry rules based on these differences. They do not coincide with
trade-ready V2 candidate events in this exported dataset, though this
does not establish full causal entry parity over all history.

**Canonical Python raw-event execution is now complete on the user's
VPS** (results above). Both bullish and bearish FVG event flags matched;
MSS flags differed on 66 bars, consistent in count with the reconstruction,
but we cannot promote the reconstruction's exact stage/window classifications
to independently verified canonical conclusions without timestamp-level
intersection. **Barchart price/contract parity remains unchecked.**

## Limitations and minimal next MVP gate

The chart CSV starts at **08:02 ET**, so it omits the earlier 04:00–08:01
premarket session, prior RTH and other liquidity-registry history. Thus
it cannot independently reconstruct complete PMH/PDH levels or verify
Barchart-to-TradingView price/roll parity. Many level plot columns are blank
when `Show sweep levels` is disabled, even though the Pine setup flags exist.

**Next (single MVP gate):** Review one *full* linked Python
sweep/displacement/MSS/FVG/retest/entry decision against the known
September 29 09:37 ET Pine short **when prior RTH, 04:00–09:30 premarket
and any required warmup bars are available**. The current chart CSV
begins at 08:02 ET and is insufficient to independently rebuild all
session levels. If it is not possible without more work/data, explicitly
mark full setup parity *unproven* and move on to MVP paper trading rather
than inventing a clean bill of health. Do not re-run the same raw audit,
loosen thresholds, re-optimize exits, or touch the 2025-H2 holdout.

All updates confined to `feature/tradingview-pinescript`; original
Pine V2 strategy and `main` remain untouched.
