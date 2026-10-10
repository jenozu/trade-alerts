# Python → Pine v6 parity checklist

Source references inspected on main: `config/strategy.yaml`, `config/sessions.yaml`, `src/backtest.py`, `src/fvg.py`, `src/structure.py`.

| Concern | Python source of truth | Requirement before Pine strategy parity claim |
| --- | --- | --- |
| Contract | strategy.yaml: MNQ, tick size 0.25, $2 per point | State MNQ/NQ contract and volume feed explicitly; avoid mixing volume baselines |
| Master bars | sessions.yaml: 1m; 2m/3m/5m/15m/30m/1h/4h/daily supported | Use completed-bar data and record chart resolution |
| Strategy hours | sessions.yaml: 09:30–10:30 America/New_York, new entries only | DST-safe session logic |
| HTF context | strategy.yaml: intraday 1h/30m/15m; macro 4h/1d context only | Closed HTF bars; macro cannot silently veto intraday signals |
| Sessions | sessions.yaml: premarket 04:00–09:30; London 02:00–05:00; Asia 20:00–00:00; Globex 18:00–17:00 | Match as-of availability / futures session date |
| PDH / PDL | sessions.yaml: previous RTH 09:30–16:00 | Do not substitute a generic previous daily candle |
| OR5/OR15/OR30 | available 09:35/09:45/10:00 | Do not reference incomplete opening ranges |
| Structure | src/structure.py: BOS/MSS/CHOCH and displacement settings | Translate settings and causal swing confirmation, don't replace with arbitrary crossover |
| FVG | src/fvg.py: min size, touch/fill, hold, inverse gap rules | Confirm three-bar boundaries and availability delays |
| Stops / targets | src/backtest.py: configurable model, slippage, fee, TP1–4, conservative same-bar resolution | Match order timing, fill assumptions, TP sizing and expiry |
| Score | raw score 0–100 is not a win probability | Keep traceable event-level components |

## Acceptance evidence
- Bar-by-bar sample comparison covering sessions, DST, gaps and roll transitions.
- Parity test fixtures for at least one confirmed breakout and one rejection/reversal, plus rejected setups.
- Same-bar stop/target collision cases and cost modeling.
- Strategy Tester and Python trade ledger reconciliation with documented differences.
- Out-of-sample evaluation independent of parameter selection.

No formal experiment IDs or research objectives are added by this scaffold.
