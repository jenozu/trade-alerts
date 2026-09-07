# NQ / MNQ Strategy Research Questions

## Purpose

This document records the strategy questions the completed research/backtesting system should be able to answer empirically. These are hypotheses to test, not assumptions to hard-code into the strategy.

The core strategy is a **liquidity + market-structure intraday framework** with two setup families:

1. **Liquidity Sweep -> Reversal**
2. **Break -> Retest -> Continuation**

The central question at an important liquidity level is not simply **"did price break it?"** but rather:

> **Did the market accept the break, or did it sweep liquidity and reject it?**

Important levels include PMH/PML, PDH/PDL, overnight/Asia/London highs and lows, weekly highs/lows, equal highs/lows, major swing highs/lows, and other validated liquidity/structure zones.

---

## Primary Research Questions

### 1. Continuation vs. Reversal

- Which setup family performs better overall: **Break -> Retest -> Continuation** or **Liquidity Sweep -> Reversal**?
- What is the win rate, expectancy, profit factor, average MFE, and average MAE of each setup family?
- Under what market conditions does continuation outperform reversal?
- Under what market conditions does reversal outperform continuation?
- How often does an apparent breakout ultimately become a sweep/reversal?
- How often does a sweep attempt instead develop into genuine acceptance and continuation?

### 2. Level-Specific Performance

- Which liquidity levels produce the best setups?
- How does performance differ at **PMH/PML vs. PDH/PDL**?
- How do Asia H/L, London H/L, overnight H/L, weekly H/L, equal highs/lows, and major swing levels compare?
- Are some levels better for continuation while others are better for sweep reversals?
- Does confluence between multiple nearby levels materially improve expectancy?
- Does the distance between PMH and PML affect breakout/reversal quality?

### 3. Breakout Quality / Acceptance

- What objective features best distinguish a valid structural break from a liquidity sweep?
- Does requiring a **5-minute close beyond the level** improve continuation performance?
- How much displacement is necessary before a breakout becomes meaningfully higher quality?
- Does candle body size relative to recent median body improve breakout selection?
- Does acceptance/follow-through beyond the level matter more than the initial break itself?
- Does waiting for a retest materially improve expectancy compared with entering the initial break?
- How often does a breakout never retest, and what opportunity cost comes from requiring one?
- Does a micro BOS after the retest improve continuation performance?

### 4. Sweep / Reversal Quality

- How far beyond a level does price typically need to trade before a sweep is meaningful?
- How quickly must price reclaim the swept level for the reversal signal to remain strong?
- Is a reclaim close more predictive than a wick through the level alone?
- Does opposite displacement after the sweep materially improve reversal expectancy?
- How valuable is CHOCH/MSS confirmation after the sweep?
- Does waiting for a pullback into the resulting FVG/OB improve the reversal entry?
- Which combinations best distinguish a genuine liquidity sweep from an ordinary failed breakout?

### 5. Volume / RVOL

- Does volume confirmation improve continuation setups?
- Does volume confirmation improve sweep-reversal setups?
- What RVOL threshold, if any, provides useful separation between strong and weak setups?
- Is high volume on the breakout more useful than high volume on the retest/hold?
- Is declining volume on a pullback a useful continuation confirmation?
- Is rejection volume useful after a liquidity sweep?
- Does time-of-day normalized RVOL outperform a simple rolling-volume comparison?

### 6. Higher-Timeframe Bias

- Does alignment with HTF bias improve expectancy?
- Which timeframe contributes the most useful bias information: Daily, 4H, 1H, 30m, or 15m?
- Should continuation trades require HTF alignment while reversal trades use HTF bias differently?
- How do results change when HTF and intraday bias agree versus conflict?
- Are countertrend sweep reversals still profitable when they target nearby opposing liquidity?

### 7. Liquidity Context / Draw on Liquidity

- Does trading toward the active Draw on Liquidity improve results?
- How does distance to the next opposing liquidity pool affect expectancy and achievable R-multiple?
- Are setups stronger when the next target is clean/untouched liquidity?
- Does nearby opposing liquidity reduce continuation quality?
- Does a prior liquidity sweep increase the probability of price moving toward the opposite side of the range?

### 8. FVG / IFVG

- Does requiring an FVG after displacement improve setup quality?
- Are FVGs more useful for continuation entries or reversal entries?
- Does FVG size matter?
- Does entry on an FVG retest outperform entry immediately after displacement?
- Do IFVGs provide useful additional confirmation?
- How quickly must an FVG be revisited to remain relevant?

### 9. Order Blocks

- Does OB confluence add measurable value after the other confirmations are already present?
- Does requiring an OB reduce trade count without improving expectancy?
- Are OB retests more useful after sweeps or after continuation breaks?
- Does overlap between an OB and FVG materially improve results?

### 10. Premium / Discount

- Does premium/discount location improve reversal selection?
- Does it improve continuation selection?
- Are longs from discount and shorts from premium materially better than trades taken without this filter?
- Does premium/discount remain useful after controlling for liquidity target and HTF bias?

### 11. Time-of-Day

Compare performance in at least these buckets:

- **09:30-09:35 ET**
- **09:35-09:45 ET**
- **09:45-10:00 ET**
- **10:00-10:30 ET**

Questions:

- Which time bucket has the highest expectancy?
- Is the 09:30-09:35 period too noisy despite offering the largest moves?
- Do sweep reversals and continuation setups have different optimal time windows?
- Does waiting until after the opening volatility materially improve signal quality?
- How does trade frequency change when restricting entries to narrower windows?

### 12. Entry Confirmation

- Is a 5m confirmation close necessary?
- Does 1m confirmation improve entry precision without creating excessive false signals?
- Does 2m execution outperform 1m or 5m execution?
- Which confirmation sequence provides the best balance of expectancy and trade frequency?
- How much performance is lost by entering later after additional confirmation?

### 13. Stop-Loss Placement

- How does a fixed **20-25 point stop** compare with structure-based stops?
- What is the MAE distribution of winning trades?
- How often would winning setups survive 15, 20, 25, 30, or 35 point stops?
- Does stop requirement differ between continuation and reversal setups?
- Does volatility-adjusted stop placement outperform fixed-point stops?

### 14. Profit Targets / Trade Management

Evaluate the current reference targets:

- TP1: **+25 points**
- TP2: **+50 points**
- TP3: **+75 points**
- TP4: **+100 points or structure/liquidity target**

Questions:

- What percentage of valid trades reaches each target before stop?
- What are typical MFE and MAE distributions by setup family?
- Does partial profit-taking outperform a single fixed target?
- Does targeting actual liquidity outperform fixed point targets?
- How often does price reach TP1 and later reverse to the stop?
- What trailing or break-even rules, if any, improve expectancy rather than merely win rate?

### 15. Market Regime / Day Type

- How do results differ on trend days, range days, high-volatility days, and low-volatility days?
- Which features identify the likely day type early enough to be useful?
- Are continuation setups substantially better on trend days?
- Are sweep reversals substantially better on range/mean-reverting days?
- Does signal-to-noise (SNR) meaningfully identify conditions in which the strategy should stand aside?

### 16. Confirmation Ablation

Test the strategy incrementally rather than assuming every concept adds value:

1. Baseline level breakout/reaction
2. + Retest
3. + Volume/RVOL
4. + HTF bias
5. + Liquidity sweep context
6. + Displacement
7. + FVG
8. + Draw on Liquidity
9. + Premium/Discount
10. + Order Block

For every addition ask:

- Does expectancy improve?
- Does profit factor improve?
- Does drawdown improve?
- Does MAE improve?
- How much trade frequency is lost?
- Is the improvement stable out-of-sample?
- Does the feature add unique information, or merely duplicate another filter?

### 17. Confluence Score

- Which components deserve the greatest weight in the confluence score?
- Are some confirmations redundant and therefore being double-counted?
- What score thresholds meaningfully separate poor, average, and high-quality setups?
- Does a higher raw score actually correspond to better realized expectancy?
- Can the score eventually be calibrated without falsely presenting it as a win probability?

### 18. Robustness / Generalization

- Are results stable across 2023, 2024, 2025, and 2026 rather than concentrated in one period?
- Do parameter choices remain effective out-of-sample?
- Are results dependent on a small number of unusually large winners?
- Are continuation/reversal conclusions stable across volatility regimes?
- Does the strategy remain viable after realistic slippage and commissions?
- Are findings robust when tested on MNQ execution assumptions rather than only NQ price movement?

---

## Core Outputs the Research System Should Produce

For every major question, report enough information to avoid judging a filter only by win rate:

- Trade count
- Win rate
- Expectancy per trade
- Profit factor
- Average win / average loss
- Median trade result
- MFE
- MAE
- Maximum drawdown
- Target-hit distribution
- Stop-hit distribution
- Setup family
- Triggering liquidity level
- Entry time bucket
- HTF/intraday bias state
- Volume/RVOL state
- Displacement state
- FVG/IFVG state
- DOL context
- Premium/discount context
- OB context
- Confluence/raw score

Results should be available both **overall** and segmented by setup family, level, time bucket, and relevant market regime.

---

## Guiding Principle

The finished system should not be designed to prove that the existing discretionary strategy is correct. It should determine **which parts of the strategy actually add predictive or risk-management value, which are redundant, and under which conditions each setup should or should not be traded.**
