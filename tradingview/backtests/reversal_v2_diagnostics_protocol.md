# MNQ Reversal V2 — read-only stage diagnostic protocol

**Branch:** `feature/tradingview-pinescript`
**Research script:** [nq_sweep_reversal_v2_diagnostics.pine](../strategies/nq_sweep_reversal_v2_diagnostics.pine)
**Frozen baseline:** [nq_sweep_reversal_v2_research.pine](../strategies/nq_sweep_reversal_v2_research.pine)
**Source integrity check:** [test_v2_diagnostics_source_parity.py](../tests/test_v2_diagnostics_source_parity.py)

## Purpose and scope

Explain which *simplified Pine V2* setup stages complete and why active
setups stop progressing, without revising entry conditions, stops, targets,
holding times, contract sizing, or orders.

This is NOT Python strategy parity; it is a visibility instrument for the
research candidate. The diagnostic file is a **separate TradingView strategy**,
not an auto-synced extension of existing TradingView saved scripts. The
original V2 is untouched. No alerts, webhooks or live orders are sent.

The diagnostic script copies the baseline trading source byte-for-byte
except for the strategy display title and three named `DIAG-ONLY` sections.
The sections only read pre/post state and increment their own counters or
draw plots, labels, and a table. The test checks this invariant by stripping
those sections and comparing source with the original. Passing a static test
does **not** establish Pine compilation, equivalent broker-emulator results,
or signal correctness.

## Loading into TradingView

1. Keep the existing **MNQ REV v2** saved; do not overwrite it.
2. On **CME_MINI:MNQ1!** using **1-minute candles**, open Pine Editor.
   Create a NEW strategy script, paste all content of the diagnostic .pine
   file linked above, save as **MNQ V2 Diagnostics**, and **Add to chart**.
   If needed, temporarily hide the original V2 strategy to avoid duplicate
   stage marks.
3. Confirm Pine Editor has **no compile or runtime errors**. GitHub cannot
   compile Pine v6; do not mark this complete until TradingView confirms it.
4. For a like-for-like Strategy Report run, check **Properties** again on the
   NEW strategy: **1 fixed MNQ**, commission **USD $0.50 per contract per side**
   (based on the user's Lucid rate; confirm full fees), **1 tick slippage**,
   **High bar detail / Bar Magnifier**, and original $50k study equity.
   Confirm all V2 Inputs (25-point stop, +50-point terminal target, 60 bars
   maximum, 09:30–10:30 ET entry restriction).
5. Deep Backtesting date: **2025-01-01 through 2025-06-30**. Select
   **Update report** if necessary.
6. Compare the new Strategy Report with the baseline before interpreting
   diagnostics. Previously observed result: **12 trades, net -$16**, with
   12 × USD $1 round-trip fees. This is a reference, not proof that the
   new study will exactly reproduce all executions. Inspect any divergence
   before changing a setting or the entry algorithm.

## First external regression check — 2026-10-11

The user uploaded the original V2 `MNQ_REV_v2_CME_MINI_MNQ1!_2026-10-10.csv`
and the new diagnostic `MNQ_V2_DX_CME_MINI_MNQ1!_2026-10-11.csv`.

Comparing the original CSV bytes and all 24 report rows shows **byte-for-byte
identical exports** (both SHA-256:
`64b855a9cae6343fc2022f25e8de4495a5297e8262491ac85e15780b385d2185`).
All 12 paired trades match in number, side, entry/exit time, entry/exit price,
durations, excursion fields, outcome, and cumulative P&L. This establishes
ledger-level regression parity **for the specific exported settings**, not full
Python signal parity.

**Historical note:** The initial diagnostic export and original baseline
were fee-free and byte-for-byte identical. A later uploaded **commission-adjusted
diagnostic export** was confirmed by the user (regardless of its CSV filename)
and verified trade-by-trade. See the section below. The CSV does not include
stage flags and cannot itself verify Bar Magnifier settings.

## Commission-adjusted diagnostic V2 export — 2026-10-11

The user explicitly confirmed that the updated CSV `MNQ_REV_v2_CME_MINI_MNQ1!_2026-10-11.csv`
came from **the correct diagnostic Pine script** despite its export filename.
TradingView-generated filenames are not reliable script identifiers, so do
not infer strategy identity from exported filenames in subsequent comparisons.

A prior comparison of the 24-row updated CSV with the fee-free baseline
found that all **12 simulated trades** matched in entry/exit timestamp,
price, direction, quantity, and outcome. There were **4 winners / 8 losers**,
gross trading P&L **-$4**, with **$12 total** ($0.50 per side on each of 12
round trips) and resulting net P&L **-$16**.

**Acceptance for trade-ledger parity:** satisfied for the uploaded historical
CSV samples **based on the user's explicit script confirmation** plus row-level
comparison. This does not establish Python/Pine stage-event parity, independently
confirm High bar-detail settings, or prove Pine history across other windows.

**Next:** inspect diagnostic stage counts and blocked/expired setups from the
chart table/Data Window. No additional CSV or commission reconfiguration is
needed merely to resolve export naming.

## How to read the chart

In **Inputs → Diagnostics**:
- `Mark detection stages`: enabled by default. Below candle = long,
  above candle = short: `SW` is sweep; `D` displacement; `M`
  MSS **proxy**; `F` linked one-minute FVG created; `E` order signal.
  These are completed-candle *research events*, not executed fills.
- `Show timeout/invalidation labels`: disabled by default. When enabled,
  labels specify whether the active candidate timed out awaiting
  displacement, MSS, FVG or its retest, or the FVG was invalidated.
  Old labels may be removed automatically when TradingView's label limit
  is reached.
- `Show event totals (loaded chart bars)`: enabled by default.
  Lower-right table totals stages, timeouts, invalidations, new-sweep
  restarts and Globex resets separately for longs and shorts.

The `T` event means a valid FVG hold occurred outside the eligible
**next-bar open** entry window; `B` means another simulated position was
already open. These events are **not terminal rejections**: the candidate
may qualify later. Each blocking category is counted at most once per
individual tracked FVG, not once per bar. Some candidates can appear
in multiple totals (e.g. blocked, then entered). Totals are **not a funnel
of mutually exclusive outcomes**.

The dashboard counts **candles loaded on the visible chart**, NOT exactly
the Deep Backtesting report's date window. TradingView Deep Backtesting
does not display all historical simulated trades on the price chart. To
investigate a dated bar, navigate to the historical timestamp on the
**regular 1-minute chart**, with the diagnostic strategy loaded.
The Data Window also contains `Diag ...` 0/1 event series and the stage
of timed-out candidates. Use chart-data export only if numerical event
comparisons become necessary; the Deep Backtesting trade-list CSV alone
does not contain stage diagnostics.

## 2026-10-11 diagnostic dashboard screenshot — observational findings

The user displayed **MNQ1! 1-minute** with diagnostic strategy **MNQ V2 DX**
visible. Chart crosshair was near 2026-10-09. The dashboard counts
**currently loaded chart bars**; these are NOT the 2025-H1 Deep Backtesting
stage counts. Unknown loaded-bar start/end boundaries and chart feed
settings mean these cannot yet be treated as one controlled population.

| Observed row | Long | Short |
| --- | ---: | ---: |
| Sweeps | 70 | 81 |
| Displaced | 28 | 30 |
| MSS proxy | 4 | 7 |
| Linked FVG | 3 | 6 |
| Entry signals | 0 | 1 |
| New sweep reset | 21 | 29 |
| Timeout: no displacement | 24 | 24 |
| Timeout: no MSS | 21 | 21 |
| Timeout: no FVG | 0 | 0 |
| Timeout: no retest | 1 | 1 |
| FVG invalidated | 2 | 4 |
| Retest outside window | 2 | 4 |
| Retest while in trade | 0 | 0 |
| Globex resets | 1 | 1 |

Stage totals: **151** sweeps, **58** displacement completions,
**11** MSS proxy completions, **9** linked FVG creations and **1** order signal.
They are *event counts*, not mutually-exclusive candidate denominators:
fresh sweeps restart contexts, blocked retests can be counted separately
from later acceptance, and truncation of chart history shifts results.
It is invalid to compute conversion or rejection percentages using these
totals as if they were the same cohorts.

**Research question 1 — MSS:** 42 timeouts awaiting an MSS proxy (21/21)
and only 11 completed MSS proxy stages were observed. Check causal swing
confirmation, pivot ties, trend classification, and broken-level deduplication
against Python; this does NOT yet establish that Pine wrongly rejected them.

**Research question 2 — entry window/retest:** six FVG invalidations,
six hold observations outside entry window, and two timeouts before FVG hold.
Separate actual failure to retest from valid-but-outside-entry-window
retests. The screenshot cannot establish trade-level chronology.

**Locked behavior:** No entry filter, threshold, expiration, stop, or
target changes based on these counts. Next validate timestamp-aligned
Pine and Python MSS/FVG event flags using identical MNQ one-minute source
bars, before coding any rule-change variant.

## Next tool: independent raw MSS/FVG comparison

A read-only [Python-vs-Pine raw-event audit](../audit/README.md) has
been added on this branch. It runs the canonical Python modules on
the same TradingView 1-minute chart candles (and optionally checks
independent OHLC against TradingView candles). This is not a parameter
optimization or a trade generator.

**Awaiting first chart-data CSV**, which must contain OHLC and Pine
Data Window indicator series, NOT the Strategy Report trade-list CSV.
The audit is designed to quantify exactly when the Pine MSS proxy
and raw FVG creation disagree with the Python event calculations.
No mismatch rates or strategy improvements can be claimed yet.

## Acceptance criteria before implementing V3

- [x] Diagnostic strategy was loaded and produced chart stage table in TradingView on MNQ 1m (user screenshot).
- [ ] Exact Pine Editor saved revision and Bar Magnifier setting independently evidenced (fee-adjusted 12-trade CSV and user's setting confirmation recorded).
- [x] User-confirmed diagnostic script recorded the same 12 entry/exit trades with commission-adjusted -$16 result; individual fills matched the original ledger.
- [ ] Inspect at least one valid winner, losing setup and incomplete/expired
      setup with `SW → D → M → F → E` versus stage timeout.
- [ ] Compare at least one such observed event sequence to the **actual**
      Python liquidity/structure/FVG/entry rules on matching MNQ source data,
      including pivot confirmation delay and timestamp timezone.
- [ ] Identify whether the bottleneck is incomplete signals, entry eligibility,
      raw data differences, or genuine Python–Pine rule mismatch.
- [ ] Reserve 2025 H2 as holdout; do not tune against it while developing V3.

The code's 2/2 swing-based MSS flag is a **proxy**, and the single linked
FVG is not Python's full object lifecycle. A correct Pine diagnostic report
does **not** certify production equivalence or profitability.

## Static regression check

Run from the repository root:

```bash
python -m pytest tradingview/tests/test_v2_diagnostics_source_parity.py -q
```

The source-integrity guard is separate from TradingView Pine Editor
compilation and historical fill verification. It must not be represented
as broker-emulator integration testing.
