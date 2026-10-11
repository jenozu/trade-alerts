# MNQ Sweep Reversal V2 — First Deep Backtesting baseline (2025 H1)

**Recorded:** 2026-10-10
**Research status:** OBSERVATION ONLY; unqualified candidate. No edge, parity, or production approval.
**Input:** User-provided TradingView Strategy Report trade-list CSV named `MNQ_REV_v2_CME_MINI_MNQ1!_2026-10-10.csv`. Raw report not committed.
**Pine source:** `tradingview/strategies/nq_sweep_reversal_v2_research.pine` on `feature/tradingview-pinescript`; the actual saved Pine Editor revision/input settings must be checked for exact version parity.
**Symbol displayed:** `CME_MINI:MNQ1!`; chart/Deep Backtesting sample shown in user screenshot as 2025-01-01 to 2025-06-30.
**No live trades:** Pine strategy() broker-emulator only.

## Reproducible summary from the trade list

- 12 paired entry/exit trades; 1 MNQ each. 4 wins, 8 losses. Win rate 33.3333%.
- Gross profit $400.00; gross loss $404.00; **net P&L -$4.00**, **profit factor 400/404 = 0.990099**.
- Expected result per observed trade = **-$0.3333** (before commissions); zero commissions in CSV.
- Four profit exits were +50.00 index points / +$100 each.
- Eight stop exits were -25.25 index points / -$50.50 each.
- Resulting no-fee breakeven win rate = 50.5 / (50.5 + 100) = **33.5548%**.
- Illustrative $3.00 MNQ round-trip fees per position (not a claim about user's actual provider): 12 × $3 = $36; hypothetical net P&L **-$40.00**.
- Longs: 7 trades, 3 wins, 4 losses, +$98.00. Shorts: 5 trades, 1 win, 4 losses, -$102.00. Both are too small for side selection.
- Two stop-outs show zero *1-minute bar duration* (2025-03-04 09:41 long; 2025-04-08 09:40 short). This is not itself a fill error, but intrabar order-of-events must be checked.
- Four stopped trades had at least $50 of max favorable excursion (MFE): trade IDs **1, 6, 8, 9**; note MFE is reported in **USD** and does not equal points. These observations justify a *future preregistered* exit-management comparison, not retrospective re-optimization.
- Among reported 12 closed trades, there is a streak of five consecutive losses. Do not infer full intra-trade drawdown from closed-trade P&L alone.
- Several exits occur after 10:30 ET (e.g. 10:37, 11:00). This is consistent with the strategy's **entry-only** 09:30–10:30 restriction.
- All entry/exit price differences reproduce reported P&L at **$2.00 per MNQ point**, confirming correct trade value arithmetic.
- Times in the CSV have **no timezone offset**. TradingView chart was shown in UTC-4, but session-specific timezone must be confirmed before exact Python timestamp comparison.

## Interpretation / blockers

1. The research-only V2 does **not** demonstrate positive after-cost expectancy; sample is low count, results are not statistically robust.
2. Winning positions exit at the selected TP2 50 points while losing positions lost 25.25 points. TradingView entry/exit fill mechanics and `Bar Magnifier` / historical bar-detail settings are **not established** by the CSV.
3. Core detected events (sweep -> displacement -> MSS -> FVG -> retest) **cannot be verified from the trade list**. A chart screenshot supports a visually plausible Sep 29 2026 example but not the numerical 2025 sequence. V2 Pine MSS/FVG are proxies, not certified Python production parity.
4. Continuous-futures roll-adjusted data source, commissions and precise Pine settings/revision need to be recorded before cross-year comparisons.
5. The report contains no per-minute candles, no stage flags, and no rejected-event ledger. Do **not** infer that 12 trades means exactly 12 legitimate Python production entry-valid plans.

## Next locked research steps

1. Verify TradingView Strategy Properties: MNQ1! (or specific MNQ contract), exact code revision, one fixed contract, slippage, realistic round-trip fee, Bar Magnifier and historical data settings. Keep the currently tested entry parameters frozen while diagnosing behavior.
2. Investigate the **two same-bar stop-outs** first, plus trade 9 (37.25 points of maximum favorable movement before the recorded stop). Compare fills with Bar Magnifier/intrabar data; do not assume or rewrite the outcome.
3. Obtain a small **2025 1-minute trade-window dataset** or non-proprietary per-bar stage export and check Python/Pine event sequence ordering and timestamp correctness for representative winning, losing, and rejected setups.
4. After mechanics/parity review, preregister separate research candidates (reversal detection, SNR quality gate, structural stop, profit management) without touching the existing EXP-030/R7–R12 contracts.
5. Maintain independent untouched holdout periods; do not use held-out 2025 H2 to repeatedly select changes. Deep Backtesting is a research tool, not proof of live performance.

The base Python repository, EXP-030 run request and its experiment history are unchanged by this documentation-only result log.
