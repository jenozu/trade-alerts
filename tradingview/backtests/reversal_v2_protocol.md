# Sweep-reversal V2 — research baseline and validation gates

Code: ../strategies/nq_sweep_reversal_v2_research.pine
Branch: feature/tradingview-pinescript
Status: source committed; Pine Editor compilation and trading results NOT independently confirmed.
This is a new TradingView-side implementation milestone, not an EXP-030 successor and not an accepted or profitable production strategy.

## Implemented from current Python main

- Reversal is distinct from breakout/continuation; it requires an ordered sequence.
- Long: sell-side liquidity sweep -> bullish displacement -> bullish MSS -> FVG created -> FVG retest hold -> next 1m open market entry. Short is mirrored.
- Uses approved America/New_York hours: RTH 09:30–16:00, premarket 04:00–09:30, London 02:00–05:00; ONLY new entries with next open from 09:30 through strictly before 10:30 ET.
- Prior RTH PDH/PDL is not a daily exchange-candle substitute.
- Sweeps close back through the reference level after >=1 tick penetration.
- Displacement initial thresholds from config/strategy.yaml: body/ATR >=0.80, body/previous-20-candle median >=1.80, close within extreme 25%, directional close required, relative volume filter disabled.
- Uses causal internal 2-left/2-right pivot confirmation.
- Basic three-candle FVG creation, one tracked zone per setup, separate later-bar hold before entry.
- Separate direction states; no mixing buy-side and sell-side events; contexts expire after set limits.
- One position maximum; no partial targets/breakeven; fixed stop 25 NQ points (100 ticks at 0.25) and terminal TP default +50. 60-bar holding expiry.
- Simulator capital $50k, 1 fixed contract, 1 tick slippage, commission $0 baseline to be replaced with realistic fee, illustrative margin 5%; these do NOT model a specific user's futures account or broker.

## Deliberate simplifications / parity blockers

- Full Python liquidity registry covers more levels and tracks each source identity. Pine v2 only PMH/PML, PDH/PDL, and London H/L; levelFamily input can isolate subsets.
- Python MSS classification uses deduplicated structure-break events plus internal trend and lifecycle. Pine approximates via confirmed 2/2 pivot trend and first-cross close rule; precise pivot/break events require fixture comparison.
- Python production FVG objects have explicit identifiers and respect/invalidation chronology. Pine uses a single tracked 1m gap per active reversal direction; this is NOT full fvg_chronology_v2 parity.
- Python full market-execution contract applies score, HTF bias, DOL target/object alignment, object-linked sequence, structural stop and sufficient room-to-target. Those are intentionally excluded here to isolate setup detection and avoid inventing calibrated weights.
- Pine requires separate bars for sweep and displacement and for MSS and FVG; displacement and MSS can occur together. Verify chronology against Python before interpreting missing/extra signals.
- Broker emulator same-bar stop/TP resolution is not necessarily Python's stop-first convention.
- Simulated strategy orders only, no live alerts or broker-routing.
- Continuation/breakout V1 remains in a separate file; later combined-family selection must replicate the selected_family_policy contract.

## First external check
1. In TradingView Pine Editor create a NEW strategy. Paste entire ../strategies/nq_sweep_reversal_v2_research.pine and replace the default template completely. Save as NQ Sweep Reversal | Research v2.
2. Use MNQ1! or NQ1! on 1m and record contract/feed and continuous/back-adjusted setting.
3. Confirm Pine compiles (no red compiler/runtime errors). Inspect event circles, entry triangles and simulated trades.
4. If ZERO trades, do not weaken filters immediately; inspect Data Window boolean events and longStage/shortStage diagnostics. Ordered confirmations may be rare.
5. Review at least three dated candidate sequences against Python output, including incomplete pivots, same-bar events, FVG chronology and no-lookahead.
6. Compare unchanged parameters, symbol/date window/costs with breakout V1, first on a development slice and NOT holdout.
7. Run Premium Deep Backtesting only after mechanics are correct; set realistic commissions/slippage and compare Bar Magnifier separately.
8. Record trade ledger, signals, net expectancy, drawdown, win rate, profit factor and rejected confirmations; report small sample sizes explicitly.

## Completion gates
- Pine v6 compiles in TradingView on 1m without runtime errors.
- Stages correctly advance/reset and do not access future information.
- Orders fill next bar open within entry window.
- Costs use correct NQ/MNQ contract economics.
- Independent trade / candidate sequences inspected bar by bar and divergences logged.
- Python-to-Pine differences measured and assessed.
- Reviewed comparison before combining reversal and continuation into a single strategy.

Do not edit main/phases.md or modify EXP-030 assumptions to make this backtest look successful.
