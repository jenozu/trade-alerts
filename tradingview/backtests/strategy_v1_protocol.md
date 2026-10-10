# Pine Automated Strategy V1 — Deep Backtesting protocol

**Status:** Code committed on feature/tradingview-pinescript; TradingView compilation and results **not yet independently verified**.
**Script:** ../strategies/nq_breakout_retest_v1.pine
**Intent:** Minimal *research baseline*, NOT the full Python live setup-family contract, NOT a new numbered EXP or R7–R12 objective.

## Research question
Does a close-confirmed breakout of the premarket high/low (or previous RTH high/low), followed by a later-bar retest touch and hold, show positive net expectancy with next-one-minute-open entries after realistic trading costs?

This does not yet test the dedicated liquidity-sweep/reversal family or establish profitability.

## Exact V1 setup rules
- **1-minute chart ONLY**, America/New_York timezone including DST.
- **Primary reference:** PMH/PML from 04:00–09:30 ET; optional PDH/PDL from prior *completed RTH* 09:30–16:00, exposed after next Globex 18:00 ET.
- **Entry window:** orders require a completed confirmation whose next-bar open is at/after 09:30 and **before 10:30** ET.
- **Breakout:** current 1m close >= upper level + one minimum tick (bullish) or <= lower level - one minimum tick (bearish), and previous close on the non-breakout side.
- **Pending setup:** at most one; invalidate if close crosses back through level beyond a one-tick buffer; expire after five 1m bars (research parameters).
- **Retest:** on a *later* completed bar (not the breakout bar), touch at or within four ticks of the level and close at least one tick beyond it in breakout direction; if valid, create a market entry **at the NEXT 1m open**, not retest limit fill.
- **Position policy:** pyramiding=0, no partial exits, no default breakeven.
- **Exit:** single full-position terminal profit target selectable from TP1 +25, TP2 +50 (initial default), TP3 +75, TP4 +100 NQ points. Initial fixed stop = 25 NQ points; deliberately a simplification of Python's preferred **structural** stop framework, not an assertion of parity. Use a relative tick stop/target bracket placed with the entry command so protective levels are anchored to the *actual simulated entry price*.
- **Expiry:** 60 one-minute bars held; market close command is filled no earlier than next available tick.
- **Default costs:** slippage 1 tick per order fill; commission currently **zero** (must set an actual fee estimate for net comparisons). The script has a $50,000 sample capital, 1 contract and **5% illustrative strategy margin**, NOT your broker's actual margin rule.

Important deviations from Python include: fixed rather than structural stop; simplified breakout/retest detection and no objective-linked Python production setup-family flags; no FVG, displacement, BOS/MSS, confluence, SNR or DOL trade gate; selected single terminal TP instead of full trade milestones in the ledger; no hard stop-first resolution for ambiguous same-1m-candle fills (TradingView broker emulator may choose another path). These deviations MUST NOT be silently treated as engine parity or retroactive research changes.

## First TradingView Premium acceptance steps
1. Open **NQ1! or MNQ1!** on 1 minute. Record full exchange/contract, adjustment/rollover and subscription feed. Historical continuous contracts may be back-adjusted; don't silently mix them with the existing raw contract history.
2. Open Pine Editor > New strategy (or clear the full editor), paste **the entire source** from the linked file, Save, Add to Chart.
3. Confirm Pine v6 compiles, orders occur in the Strategy Tester, and there are no runtime errors. If no trades show, verify enough historical 1m data includes 04:00–09:30 ET AND the comparison date range, and check simulated equity/margin.
4. Under Strategy Properties: use **1** contract, correct futures point value, initial capital, realistic **round-turn commission** and slippage; record assumed long/short leverage/margin. Do not publish commission-free P&L as after-cost.
5. Turn **Bar Magnifier** on (when available), and capture if it changes fills. Bar Magnifier improves resolution but still needs reconciliation and is subject to data coverage limits.
6. In Strategy Tester > Deep Backtesting, choose a locked development historical date range. Record start/end, symbol, market feed/roll adjustments, entire Pine source version, selected level family, fee, slippage, capital, margin, inputs and number of trades.
7. Export the Strategy Report/trade list; compare setup frequency, entries, stops/targets, win rate, net expectancy, drawdown and maximum favorable/adverse excursion where possible against independently generated Python ledgers under matching assumptions.
8. Keep a separate untouched holdout time span. **Do not pick the best parameters using holdout performance**.
9. Only after we inspect and reconcile the baseline should we separately test reversal setups, SNR filters and Python-equivalent scoring.

## Manual checks before results are interpretable
- 09:30 ET premarket extrema are frozen; next-open entries must stay strictly before 10:30.
- 09:30–09:34 breakout cannot retest in the SAME breakout candle.
- Missing/sparse chart history may make PDH/PDL unavailable; don't treat na as level zero.
- Check a normal date, DST transition, and Sunday/Monday session before trusting RTH/prior-day levels.
- On any stop/TP hit in the same 1m candle, record the simulator fill assumption; Python reference prefers stop-first and the results are NOT directly interchangeable.
- Chart or Strategy Properties overrides to process orders on closing tick or to change order execution recalculation can invalidate next-open semantics.
- No live trading, order-fill alerts, automated broker connections or webhook execution are part of this baseline.

## Report template
- Pine commit SHA / date:
- Symbol / contract / continuous adjustment:
- Chart timeframe / feed:
- Deep Backtesting date start/end / sessions covered:
- PMH/PML or PDH/PDL / retest settings:
- Position quantity / initial capital / illustrative margin:
- Commissions / slippage / Bar Magnifier:
- Total trades / net profit / win rate / profit factor / max drawdown:
- Entry timing + stop/TP spot checks:
- Same-bar fill ambiguities / missing history:
- Python replay comparison:
- Decision: reject / investigate / candidate for independent validation
