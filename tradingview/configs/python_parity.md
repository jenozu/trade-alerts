# Python → Pine Script v6 parity checklist

Compared main: config/strategy.yaml, config/sessions.yaml, src/snr.py, src/fvg.py, src/structure.py, src/backtest.py, src/trade_planner.py. The Pine **indicator V1** is an initial visual/telemetry implementation, not a parity-certified production market-state engine.

| Concern | Python source of truth | Pine v1 status |
| --- | --- | --- |
| Contract | strategy.yaml MNQ, 0.25 tick, $2 per MNQ point | Uses chart's actual symbol/tick; requires user to choose correct traded contract/feed |
| Bars | Session-aware UTC 1m, resampled 2m/3m/5m/15m/30m/1h/4h/daily | 1-minute only enforced; HTF context uses previous confirmed HTF bars |
| Entry window | 09:30–10:30 America/New_York | Implemented as research marker/window flag, NOT an order gate yet |
| Intraday HTF bias | Structural 1h/30m/15m with Python weights 3/2/1; macro 4h/daily is context only | **Not implemented**; confirmed 15m/30m/1h close vs EMA21 display proxies only |
| Sessions | London 02–05, premarket 04–09:30, Asia 20–00, overnight 18–09:30 | Implemented for 1m, manual DST/sample verification required |
| PDH/PDL | Prior completed RTH 09:30–16:00, available next Globex 18:00 | Implemented using rolling RTH accumulator and next-Globex publication; verify |
| OR5/OR15 | Known after 09:35/09:45 | Implemented with availability flags; verify |
| VWAP | strategy.yaml reset Globex 18:00; **sessions.yaml says RTH open 09:30** | **Unresolved existing config discrepancy**; input selectable, default Globex |
| SNR | abs(5-bar net movement)/SMA(14 true range), quality only | Approximate 1m formula matched; requires Python numerical fixture comparison |
| RVOL | Time-of-day RVOL and rolling previous 20-bar baseline | Rolling 1m previous-bar RVOL only; time-of-day RVOL deferred |
| Swings | 2/2 confirmed internal, 5/5 external; causal delay | 2/2 confirmed pivot and simple close break only; does not yet implement full BOS/MSS/CHoCH |
| Liquidity sweeps | 1 tick through level, close back, rich level registry | Basic PDH/PDL PMH/PML LOH/LOL rules; other liquidity families deferred |
| FVG | 3-candle gaps; age 20; retest hold; IFVG lifecycle | New 1m FVG, later hold and invalidation; complete Python-equivalent lifecycle deferred |
| DOL | Target selection and evidence scoring | Deferred |
| Confidence | Python 0–100 raw confluence not probability, SNR is non-directional | No confluence or probability score invented |
| Stops/targets | Structural buffer 2 points; preferred 20–25 points; TP milestones 25/50/75/100 | Not in indicator V1; future separate strategy |
| Execution model | After confirmed retest; next bar; conservative same-bar resolution; no partials/BE initially | Strategy unimplemented |

## Requirements before claims of parity
- Compare 1m level and indicator values to Python for sample days, daylight-saving transitions and futures rolls.
- Check previous RTH level publication, opening-range finish times, sweep closes and FVG creation/retest/expiry.
- Test sample source candles and null/missing-data states.
- Confirm Pine compiles via actual TradingView Pine Editor; no local Pine compiler is available here.
- Before strategy trading: test next-bar entry, stop/target collision, costs, conservative sequencing, real future contract point values, stale-data handling, rejected setups and holdout splits.
- Keep indicator research events independent from order entry decisions.

No EXP numbers or new R7–R12 research objectives were created.


## Strategy V1 cross-engine differences (open)
- New script: strategies/nq_breakout_retest_v1.pine — Pine broker emulator simulation.
- **Matching intended entry timing:** signal at confirmed 1m retest bar close; strategy.entry() normally fills next 1m open because process_orders_on_close=false.
- **Simplified breakout/retest:** Uses session high/low break and simple wick-touch/close-hold with independent adjustable five-bar expiry. Python live model requires a linked production family and fresh event.
- **Fixed 25 point stop:** This is NOT Python structural + buffer stop parity.
- **Terminal TP2 (+50) by default:** TradingView closes at the selected target; Python tracks four milestones and may use TP4 as terminal under current research model.
- **One trade at a time**, no initial BE or partial exits, default max 60 minutes.
- **Fill ambiguity:** TradingView broker-emulator same-bar stop/TP resolution is not Python's explicit conservative stop-first convention.
- **Test economics:** Pine initial equity $50k, 1 contract, slippage one tick, default commission zero (must be set) and 5% example margin — not an account specification.
- **HTF, SNR, FVG and reversal:** not used to authorize a trade yet, as V1 is explicitly an incremental no-filter baseline.
- Manual Pine compile, backtest, historical session-level parity, rollover and sample fill comparison remain pending.
