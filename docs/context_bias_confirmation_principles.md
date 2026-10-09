# Strategy Development Principles — Context, Bias, and Confirmation

This note records a strategy-development rule for future research, experiments, backtesting, live analysis, and alert logic in `trade-alerts`.

## Core principle

Do not infer session bias from a single lower-timeframe structure event.

A lower-timeframe CHoCH can represent:
- a true reversal,
- a countertrend retracement,
- a liquidity reaction,
- or a temporary internal structure shift inside a larger directional move.

Therefore, CHoCH should be treated as evidence, not as an automatic bullish/bearish session-bias switch.

## Separate context from trigger

Future analysis and research should distinguish:

1. **Higher-timeframe / intraday context**
   - prevailing directional structure
   - major liquidity draws
   - premium / discount location
   - prior session and overnight structure

2. **Lower-timeframe momentum**
   - BOS / CHoCH
   - displacement
   - short-term trend / retracement state
   - volume / SNR / RVOL context

3. **Location**
   - premarket high / low
   - Asia high / low
   - internal range boundaries
   - VWAP / equilibrium
   - FVGs / liquidity pools / key swing levels

4. **Confirmation levels**
   - explicit bullish trigger
   - explicit bearish trigger
   - invalidation level
   - retest / acceptance criteria

5. **Trade trigger**
   - only activate a setup when its confirmation condition is satisfied
   - do not equate a directional lean with an executable trade

## Prefer state descriptions over simplistic probability calls

Morning analysis should prefer language such as:

- HTF / intraday context: bearish
- 5m momentum: bullish retracement
- location: approaching overhead resistance
- bullish confirmation: acceptance above X
- bearish confirmation: loss of Y

Avoid presenting a simple bullish/bearish percentage as the primary conclusion unless the probability is explicitly derived from validated historical research.

## Confirmation-based trade plans

Each scenario should define:

- setup direction
- trigger
- entry logic
- stop / invalidation
- TP1–TP4
- what must happen before the setup becomes active
- what cancels the setup

A scenario can be the less likely contextual outcome and still become the correct executable trade if its confirmation fires first.

## Liquidity target vs reversal level

Do not assume every major support/resistance level is a reversal level.

Research and alert logic should classify important levels, where possible, as:
- **liquidity target / draw**, or
- **potential reaction / reversal zone**.

If price approaches a level with strong displacement and aligned structure, continuation through the level may be more likely than reversal.

## Internal structure vs premarket range

Do not reduce the strategy to “break the premarket high or low.”

When the premarket range is wide, internal structure may provide the more useful and earlier trigger.

Research should evaluate a hierarchy similar to:

**HTF bias/context → session liquidity → internal range → sweep/displacement → structure shift → retest/acceptance → entry**

rather than:

**premarket high/low → breakout → trade**

## Research / experiment implications

Future experiments should separately measure:

- contextual bias accuracy
- whether bullish or bearish confirmation fired first
- trade outcome after confirmation
- CHoCH continuation vs reversal behavior
- internal-range break performance vs premarket-high/low break performance
- liquidity-target continuation vs reversal behavior
- performance conditioned on HTF alignment
- performance of countertrend CHoCH signals
- MFE / MAE after confirmed triggers

This distinction is especially important for interpreting EXP-series results: a wrong initial directional lean should not be counted the same way as a triggered setup that failed.

## Design rule

The alert system should eventually represent **market state** and **trade state** separately.

Example:

```
market_context = bearish
lt_momentum = bullish_retracement
bull_trigger = 31268
bear_trigger = 31200
active_trade = none
```

Only after a valid trigger / confirmation should `active_trade` change.

---

This document is a research and design principle, not proof that the current implementation already enforces all of these rules. Any production logic change should be validated with historical data before being promoted into live alerts.
