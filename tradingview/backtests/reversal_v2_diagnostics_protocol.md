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

## Acceptance criteria before implementing V3

- [ ] New diagnostic .pine compiles and runs in TradingView on MNQ 1m.
- [ ] Test window, source revision, user inputs, fill detail and fees recorded.
- [ ] Deep Backtesting entry/exit ledger matches V2 under identical settings
      (not merely its total net P&L); if not, reconcile before proceeding.
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
