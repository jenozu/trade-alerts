# Indicator V1 review / manual acceptance (2026-10-10)

## Source and scope
Built from the **separate** uploaded 280-line legacy Pine script named "strategy.pine" and current main-branch Python configs, with Python definitions prioritized. Legacy script used strategy() without any strategy.entry/exit calls. This new file uses indicator() and intentionally does not create simulated or live orders.

## Included in V1
- London 02:00–05:00 ET, premarket 04:00–09:30 ET, Asia 20:00–00:00 ET, overnight 18:00–09:30 ET.
- PDH/PDL from previous completed RTH (09:30–16:00), frozen at next Globex start 18:00.
- Opening range 5 and 15 minutes; available only after 09:35/09:45 ET.
- VWAP typical price × volume; user-selectable Globex/RTH reset. **Open discrepancy to reconcile:** config/strategy.yaml specifies Globex 18:00, while config/sessions.yaml has vwap.reset=rth_open. Current indicator defaults Globex to reflect strategy.yaml, but parity is unresolved.
- EMA9/EMA21, 1m SNR quality = abs(5-bar net change) / simple 14-bar ATR, 20-previous-bar rolling RVOL.
- Confirmed 2-left/2-right swing pivots, simple swing-close breaks (not yet authoritative BOS/MSS/CHOCH).
- 1-minute 3-candle FVG, later close-hold/close-through invalidation and max-age 20-bar reference zones.
- Tick-penetration + close-back buy-side/sell-side reference sweeps at PDH/PDL, PMH/PML and London H/L.
- Confirmed 15m/30m/1H close vs EMA21 **context proxies** displayed separately (NOT Python HTF bias).
- Optional 1m/5m JSON snapshots from confirmed candles and event-specific research alerts.
- Data Window feature outputs useful for chart export.

## Deliberately not included yet
- Authoritative Python structural bias, DOL target selection, calibrated confluence score, order-block validation, IFVG lifecycle, SMT comparison, actual long/short entry decisions or horizontal entry/SL/TP overlays.
- The old signed SNR direction, ATR×2.5 trading plan, rolling-30-bar pseudo-premarket, developing daily high/low, and restrictive all-eight-filters-together trade conditions.
- Live auto-trading, broker connectivity, running webhook alerts or a receiver.

## Manual acceptance (must run in TradingView)
1. Add indicator on 1m MNQ/NQ with correct futures contract and paid exchange feed; confirm it compiles in Pine v6. **Not verified in this environment**.
2. Check 02:00–05:00 London and 04:00–09:30 premarket including overlap, overnight/Asia midnight behavior, Monday gaps and DST transitions.
3. Compare displayed levels with Python session output for known historical sessions; inspect previous RTH H/L on 18:00 refresh.
4. Validate FVGs and sweep flags bar-by-bar against Python. Document any differences instead of claiming equivalence.
5. Verify chart export includes Data Window plot fields and values are not leaking incomplete HTF bars.
6. If telemetry is enabled later, create **Any alert() function call** alert and validate JSON receiver with a test endpoint before connecting VPS; check nulls and duplicates.
7. Do not allow the indicator to issue trading orders. Order entry belongs in a separate strategy and execution gateway.

## Next iteration candidates
Approved intended capabilities: proper Python-equivalent market-state/bias, breakout vs sweep-reversal classification, validated trade-plan overlay lines entry/SL/TP1–TP4, SNR/confluence (separate from support/resistance confluence), IFVG lifecycle, chart layout refinements and optional live analysis events. Implement these in a reviewed incremental order; do not invent historical experiment identifiers.
