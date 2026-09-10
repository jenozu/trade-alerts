# NQ / MNQ Strategy Refinement Roadmap

## Purpose

This roadmap defines the formal strategy-refinement process to follow after the untouched historical baseline is established.

The goal is **not** to optimize for the prettiest backtest or highest historical net profit. The goal is to determine, empirically and reproducibly:

- which parts of the current strategy actually add edge;
- which confirmations are redundant or harmful;
- which setup families work best under which conditions;
- whether the current 0-100 confluence score genuinely separates high-quality from low-quality trades;
- how entries, stops, targets, and trade management should be changed;
- whether any improvement survives across years, regimes, and held-out data.

This document is the strategy-refinement companion to:

- `docs/PHASE12_BACKTESTING_PLAN.md`
- `docs/strategy_research_questions.md`
- `phases.md`

The research process must remain deterministic, reproducible, archived, and resistant to overfitting.

---

# 1. Core strategy being refined

The current framework is a **liquidity + market-structure intraday strategy** with two primary setup families:

1. **Liquidity Sweep -> Reversal**
2. **Break -> Retest -> Continuation**

The central decision at an important level is:

> Did price accept the break, or did it sweep liquidity and reject it?

Important context includes:

- PMH / PML
- PDH / PDL
- overnight high / low
- London high / low
- Asia high / low
- weekly high / low
- equal highs / lows
- major internal and external swing levels
- VWAP
- support / resistance confluence
- premium / discount
- HTF bias
- liquidity sweeps
- displacement
- MSS / BOS / CHOCH
- FVG / IFVG
- Draw on Liquidity (DOL)
- volume / RVOL
- signal-to-noise ratio (SNR)
- room to target
- time of day

The primary strategy window remains approximately **09:30-10:30 ET**, with particular interest in the first several minutes after the cash open.

---

# 2. Untouched baseline — permanent control

Before refining anything, preserve the current strategy as the control configuration.

No future experiment should overwrite or redefine this baseline.

## Current corrected year-by-year baseline

| Year | Trades | Win rate | Expectancy points | Expectancy R | Profit factor | Net points |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2023 | 344 | 32.27% | +2.916 | +0.117R | 1.175 | +1003.00 |
| 2024 | 388 | 27.32% | +0.171 | +0.007R | 1.010 | +66.25 |
| 2025 | 486 | 24.90% | +2.270 | +0.090R | 1.122 | +1103.25 |

Combined sample:

- **1,218 trades**
- approximately **+2,172.5 net points**

The baseline should always remain available as the reference column in future experiment reports.

## Baseline rule

Every proposed change must answer:

1. What specific weakness is being addressed?
2. What is the hypothesis?
3. What single parameter family or rule is changing?
4. What result would count as an improvement?
5. Is the improvement stable across years and regimes?
6. Does it survive held-out / walk-forward validation?

If these questions cannot be answered, do not run the experiment.

---

# 3. Research discipline

## 3.1 One family of changes at a time

Never simultaneously change:

- score weights;
- entry confirmation;
- stop logic;
- target logic;
- time window;
- setup qualification.

That makes attribution impossible.

Experiment families should be isolated.

## 3.2 Preserve every meaningful experiment

Every experiment must have:

- unique experiment ID;
- hypothesis;
- Git SHA;
- input dataset / hash;
- strategy config snapshot;
- sessions config snapshot;
- exact parameter changes;
- trade ledger;
- metrics JSON;
- segmented results;
- baseline comparison;
- notes / conclusion;
- acceptance or rejection decision.

Suggested naming:

```text
EXP-001_score-bands-baseline
EXP-002_long-vs-short
EXP-003_setup-family
EXP-004_htf-bias
...
```

## 3.3 Never judge from win rate alone

Primary evaluation metrics should include:

- trade count;
- win rate;
- expectancy points;
- expectancy R;
- profit factor;
- net points / net R;
- average win;
- average loss;
- median trade result;
- MFE;
- MAE;
- MFE captured at exit;
- maximum drawdown;
- maximum losing streak;
- TP1 / TP2 / TP3 / TP4 hit rates;
- stop rate;
- average hold time;
- distribution of results, not only means.

A change that raises win rate but lowers expectancy or worsens drawdown is not automatically an improvement.

## 3.4 Sample-size discipline

Small groups should be marked as exploratory rather than treated as proof.

Whenever a subgroup appears strong, report its trade count beside the performance metric.

Avoid selecting a filter simply because a tiny subset produced unusually high profit factor.

---

# 4. Phase R0 — Baseline integrity and research freeze

Before tuning, confirm that the baseline artifacts are fixed and reproducible.

Checklist:

- [ ] 2023 baseline archived and immutable
- [ ] corrected 2024 baseline archived and immutable
- [ ] 2025 baseline archived and immutable
- [ ] corrected three-year comparison saved
- [ ] baseline strategy config hash recorded
- [ ] baseline sessions config hash recorded
- [ ] source datasets and hashes recorded
- [ ] Stage 17 data-quality warnings documented
- [ ] no strategy changes applied before baseline freeze

Stage 17 note:

The corrected logic distinguishes **required-history/session incompleteness** from **data-quality warnings**. The 2024 required sessions are covered. Minor historical gaps and extreme/large-move warnings should remain documented without being falsely labeled as missing history.

Do not alter valid historical bars merely to force a clean status message.

---

# 5. Phase R1 — Baseline decomposition

The first strategy research work should use the existing untouched trades only. No strategy parameters change yet.

The objective is to identify where the current edge is coming from and where the strategy is weak.

## EXP-001 — Score-band baseline analysis

This is the first required experiment because the score drives eventual live alert quality.

Analyze score bands such as:

- below 50, if trades exist
- 50-59
- 60-69
- 70-79
- 80-89
- 90-100

For each band calculate:

- trades;
- win rate;
- expectancy points;
- expectancy R;
- profit factor;
- net points / R;
- TP1 / TP2 / TP3 / TP4 hit rate;
- stop rate;
- average / median MFE;
- average / median MAE;
- drawdown;
- average hold time;
- long / short count;
- setup-family count;
- yearly performance.

### Score monotonicity test

A useful score should show a reasonably monotonic relationship:

```text
higher score
    -> stronger expectancy
    -> stronger profit factor
    -> better target reach
    -> better MFE / MAE relationship
```

Perfect monotonicity is not required, but if 60-69 materially outperforms 80-89 over sufficient sample sizes, investigate the score composition before trusting the score threshold.

### Important rule

The confluence score is **not a probability**.

A score of 80 must never be presented as "80% chance of winning" unless an explicit probability-calibration model is built and independently validated later.

### Implementation status (2026-09-10)

- [x] Ledger-only EXP-001 analyzer added: `scripts/run_exp001_score_bands.py`.
- [x] Analyzer produces fixed score-bucket metrics, annual and long/short segmentation, a monotonicity check, JSON, and Markdown outputs without rerunning the pipeline.
- [ ] Execute against the three archived baseline ledgers and record the observed conclusions here. The ledgers are intentionally not stored in Git.

The current score should be treated as a deterministic setup-quality rank.

---

## EXP-002 — Long vs short

Determine whether the strategy has directional asymmetry.

Compare long and short trades on:

- trade count;
- expectancy;
- profit factor;
- TP reach;
- MFE / MAE;
- drawdown;
- score distribution;
- setup family;
- year;
- time bucket;
- regime.

Questions:

- Are shorts materially stronger or weaker than longs?
- Does one direction perform poorly only in certain regimes?
- Should long and short scoring eventually use different weights?

Do not split the strategy into separate long/short configs unless evidence is stable.

### EXP-002 completed evidence — 2026-09-10

- [x] Ledger-only analyzer implemented in `src/directional_research.py`.
- [x] Runner implemented in `scripts/run_exp002_long_vs_short.py`.
- [x] Existing completed 2023, 2024, and 2025 ledgers analyzed without rerunning the 20-stage pipelines.
- [x] Markdown, JSON, and CSV outputs generated.
- [x] Trade Brain experiment/findings documentation updated.

Observed aggregate directional performance:

| Direction | Trades | Win rate | Expectancy pts | Expectancy R | PF | Net pts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| LONG | 653 | 29.9% | +2.94 | +0.118R | 1.17 | +1917.50 |
| SHORT | 565 | 25.3% | +0.45 | +0.017R | 1.02 | +255.00 |

Long-minus-short expectancy gap: **+2.49 points/trade**.

Year stability:

- 2023: LONG +2.33 / PF 1.14; SHORT +3.56 / PF 1.21.
- 2024: LONG +1.50 / PF 1.09; SHORT -1.59 / PF 0.91.
- 2025: LONG +4.63 / PF 1.26; SHORT -0.25 / PF 0.99.

Therefore, the aggregate long advantage is meaningful but **not stable in sign across all years**.

Score calibration evidence:

- 70–79: LONG +1.67 / PF 1.10 versus SHORT -0.14 / PF 0.99.
- 80–89: LONG +7.52 / PF 1.43 versus SHORT +1.04 / PF 1.05.
- 90–100 contains only 21 total trades; the eight short trades are too small a sample for a directional conclusion.
- LONG mean score 76.11 / median 74.42.
- SHORT mean score 75.36 / median 73.59.

The score distributions are similar despite materially different realized expectancy, supporting the conclusion that the current single score is not equally calibrated for both directions.

Context observations:

- HTF-aligned trades were positive in both directions, but aligned longs remained materially stronger.
- Displacement-present trades outperformed displacement-absent trades in both directions.
- Structure-shift-present trades outperformed trades without structure shift in both directions.
- FVG-present shorts were +8.48 expectancy / PF 1.50 versus -0.91 / PF 0.95 without FVG context.
- Sweep-present shorts were -1.60 expectancy / PF 0.91 versus +8.94 / PF 1.52 without the sweep flag. This is preliminary and requires dedicated EXP-007 analysis.
- Unconditional SNR and RVOL averages were broadly similar across directions and do not obviously explain the aggregate directional gap.
- The available time-bucket representation placed all trades into `10:30+`, so EXP-002 makes no valid time-of-day conclusion. Timestamp semantics must be verified before EXP-020.

EXP-002 decision: **INVESTIGATE — no strategy change**.

Separate long/short scoring is now a legitimate later research candidate, but EXP-002 does not authorize separate production weights/configs because the directional advantage is not stable across every year.

Next required experiment: **EXP-003 — Setup-family comparison (Reversal vs Continuation)**.

---

## EXP-003 — Setup-family comparison

Compare:

- Liquidity Sweep -> Reversal
- Break -> Retest -> Continuation

Required segmentation:

- overall;
- yearly;
- long / short;
- level type;
- score band;
- time of day;
- HTF alignment;
- volatility regime.

Determine whether these should eventually have separate score models or thresholds.

---

## EXP-004 — Year and regime stability

Use 2023, 2024, and 2025 separately before relying on combined results.

2024 is especially important because the baseline was nearly breakeven. Identify which components deteriorated relative to 2023 and 2025.

Questions:

- Was 2024 weakness concentrated in one setup family?
- Was it long/short specific?
- Was it caused by particular time buckets?
- Did certain score bands fail?
- Did volatility or SNR conditions differ?
- Was target capture poorer despite comparable entry quality?

A proposed refinement that "fixes" 2024 but destroys 2023/2025 should normally be rejected.

---

# 6. Phase R2 — Component contribution / ablation

The goal is to determine whether each strategy concept contributes unique predictive value.

For every component compare trades **with** the feature versus trades **without** it while preserving the rest of the baseline.

When possible, also perform incremental ablation and controlled re-runs.

## EXP-005 — Important liquidity level

Compare performance by trigger / interaction level:

- PMH / PML
- PDH / PDL
- overnight high / low
- London high / low
- Asia high / low
- weekly high / low
- equal highs / lows
- internal swing
- external swing
- confluence zone

Questions:

- Which levels create the best continuation setups?
- Which levels create the best reversal setups?
- Are PMH/PML too wide on some days?
- Does distance between PMH and PML affect setup quality?
- Does multi-level confluence materially improve expectancy?

---

## EXP-006 — HTF bias

Compare:

- aligned;
- neutral;
- conflicting;
- unknown.

Then isolate individual timeframe contribution:

- Daily
- 4H
- 1H
- 30m
- 15m

Questions:

- Which timeframe adds the most predictive value?
- Are continuation trades more dependent on HTF alignment?
- Can reversal trades profitably run countertrend toward nearby liquidity?
- Are multiple bias inputs redundant and being double-counted?

---

## EXP-007 — Liquidity sweep contribution

Measure:

- sweep present vs absent;
- buy-side vs sell-side sweep;
- sweep distance;
- reclaim speed;
- reclaim close vs wick only;
- sweep followed by displacement;
- sweep followed by MSS / CHOCH;
- sweep followed by FVG.

Determine what objectively separates a high-quality reversal from an ordinary failed break.

---

## EXP-008 — Breakout / acceptance quality

Measure:

- initial level break only;
- 1m close beyond level;
- 5m close beyond level;
- displacement threshold;
- body size relative to recent median;
- follow-through distance;
- retest present / absent;
- retest hold;
- micro BOS after retest.

Important question:

> Does waiting for confirmation improve expectancy enough to justify missed trades and later entries?

---

## EXP-009 — Displacement

Displacement showed encouraging discrimination in earlier short-sample work and deserves explicit analysis.

Compare:

- displacement present / absent;
- bullish / bearish;
- weak / medium / strong if supported;
- displacement size;
- displacement relative to ATR / recent candle range;
- displacement followed by structure shift;
- displacement followed by FVG.

Determine whether displacement deserves a larger scoring weight.

---

## EXP-010 — MSS / BOS / CHOCH / structure shift

Compare each structure event independently and in sequence.

Questions:

- Does MSS add value beyond sweep + displacement?
- Does BOS improve continuation setups?
- Does CHOCH improve reversal setups?
- Are multiple structure confirmations redundant?
- Does waiting for structure confirmation worsen entry price too much?

---

## EXP-011 — FVG / IFVG

Compare:

- FVG present / absent;
- FVG size;
- FVG direction;
- FVG created by displacement;
- retest / no retest;
- time until retest;
- respected / disrespected;
- IFVG present / absent;
- continuation vs reversal.

Do not assume FVG adds value simply because it is visually compelling.

---

## EXP-012 — Order blocks

If OB features are available and reliably encoded, compare:

- OB present / absent;
- retest / no retest;
- OB + FVG overlap;
- sweep-reversal context;
- continuation context.

Reject OB requirements if they mainly reduce trade count without improving expectancy, drawdown, or target capture.

---

## EXP-013 — Premium / discount

Compare:

- longs from discount;
- longs from premium;
- shorts from premium;
- shorts from discount;
- equilibrium area;
- internal vs external dealing range context.

Then control for DOL and HTF bias to determine whether premium / discount contributes unique information.

---

## EXP-014 — Draw on Liquidity

Compare:

- trade aligned with primary DOL;
- trade opposed to DOL;
- neutral DOL;
- high vs low DOL confidence;
- distance to primary target;
- target category;
- clean / untouched liquidity vs already-traded liquidity.

Determine whether DOL should act as:

- score contribution;
- hard filter;
- target-selection tool;
- context only.

---

## EXP-015 — Volume / RVOL

Compare:

- rolling RVOL;
- time-of-day normalized RVOL;
- breakout volume;
- retest volume;
- rejection volume;
- declining pullback volume;
- volume spike / no spike.

Test thresholds rather than assuming a specific RVOL cutoff.

Potential threshold sweep examples:

```text
RVOL >= 1.0
RVOL >= 1.2
RVOL >= 1.5
RVOL >= 2.0
```

Only promote a threshold if performance improvement is stable and sample size remains useful.

---

## EXP-016 — SNR / efficiency

Measure performance across SNR buckets and efficiency buckets.

Questions:

- Does low SNR reliably identify chop?
- Is SNR more useful as a hard no-trade filter or scoring penalty?
- Are different SNR thresholds appropriate for continuation vs reversal?
- Does SNR interact with time of day or volatility regime?

---

## EXP-017 — VWAP

Compare:

- above / below VWAP;
- reclaim / rejection;
- distance from VWAP;
- VWAP aligned with trade direction;
- VWAP conflict;
- level + VWAP confluence.

Determine whether VWAP contributes unique edge after HTF bias and structure are accounted for.

---

## EXP-018 — Support / resistance confluence

Measure performance as the number and quality of nearby validated levels changes.

Questions:

- Does multi-level confluence improve expectancy?
- Is there a point where more "confluence" is merely redundant double counting?
- Which source types deserve the most weight?
- Does proximity matter more than raw count?

---

## EXP-019 — Room to target

Measure available space between entry and opposing liquidity / structural obstruction.

Potential buckets:

```text
< 25 points
25-49
50-74
75-99
100+
```

Questions:

- Does insufficient room explain many stopped or low-MFE trades?
- Should room-to-run be a hard filter?
- Should required room vary by intended target model?

---

# 7. Phase R3 — Time and entry model research

## EXP-020 — Time-of-day buckets

At minimum compare:

- 09:30-09:35 ET
- 09:35-09:45 ET
- 09:45-10:00 ET
- 10:00-10:30 ET

Measure separately for reversal and continuation.

Questions:

- Is 09:30-09:35 too noisy?
- Does the opening period provide enough MFE to justify its additional stop-outs?
- Do reversals occur optimally at a different time than continuations?
- Does a narrower strategy window improve quality too much at the expense of frequency?

---

## EXP-021 — Execution / confirmation timeframe

Compare where technically possible:

- immediate break / sweep entry;
- 1m confirmation;
- 2m confirmation;
- 5m confirmation close;
- retest entry;
- retest + micro structure confirmation;
- mid-candle entry if the live model permits it.

Measure opportunity cost as well as improvement.

For example:

- setups lost by waiting;
- points sacrificed by later confirmation;
- reduction in false breaks;
- change in MAE;
- change in achievable TP distribution.

---

# 8. Phase R4 — Confluence scoring system calibration

This is a major formal phase, not a cosmetic adjustment.

## Objective

Create a score whose increasing values correspond to demonstrably stronger trade quality without pretending that the score is a win probability.

## 8.1 Inventory every current score component

For each score contribution record:

- feature name;
- maximum points;
- positive / negative direction;
- hard filter or soft weight;
- setup family applicability;
- possible overlap with another feature;
- sample count when triggered.

Example categories:

- important-level quality;
- HTF alignment;
- liquidity sweep;
- displacement;
- structure shift;
- FVG / IFVG;
- DOL alignment;
- premium / discount;
- VWAP;
- volume / RVOL;
- SNR;
- support / resistance confluence;
- room to target;
- time-of-day quality;
- penalties / invalidation states.

## 8.2 Component lift analysis

For every component calculate its realized incremental lift:

```text
expectancy WITH component - expectancy WITHOUT component
PF WITH component - PF WITHOUT component
TP reach WITH component - TP reach WITHOUT component
MFE/MAE improvement
```

Also compute these by year and setup family.

A component should not receive a large weight simply because it sounds important conceptually.

## 8.3 Redundancy / double-counting analysis

Examples of potentially correlated inputs:

- displacement + FVG;
- sweep + MSS;
- HTF bias + DOL;
- premium/discount + DOL;
- multiple structure-shift labels;
- support/resistance confluence + important liquidity level.

Use pairwise co-occurrence and conditional-performance analysis to determine whether two features are adding unique information or repeatedly scoring the same underlying event.

## 8.4 Reweight the score

Only after contribution analysis, test alternative weight sets.

Do not search thousands of arbitrary combinations for the historical maximum.

Use a small number of evidence-based candidates, for example:

```text
Baseline weights
Candidate A — greater displacement emphasis
Candidate B — reduced FVG weight
Candidate C — greater DOL / room-to-run emphasis
Candidate D — setup-family-specific weighting
```

## 8.5 Threshold calibration

After weights are chosen, examine candidate thresholds such as:

```text
>= 60
>= 65
>= 70
>= 75
>= 80
>= 85
```

For each threshold report:

- qualifying trade count;
- percentage of baseline opportunities retained;
- expectancy;
- PF;
- drawdown;
- net points;
- TP distribution;
- yearly consistency.

The best threshold is not necessarily the one with the highest PF if it produces very few trades.

## 8.6 Separate setup-family scores if justified

If reversal and continuation components behave materially differently, consider:

```text
reversal_score
continuation_score
```

rather than forcing every setup through the same weight model.

Only do this if the historical evidence clearly supports it.

## 8.7 Score acceptance criteria

Before calling the score calibrated:

- [ ] higher bands generally show stronger expectancy / PF;
- [ ] results are not dominated by one year;
- [ ] adequate sample sizes remain;
- [ ] no obvious double counting remains;
- [ ] score behavior holds on validation data;
- [ ] score remains interpretable;
- [ ] score is not presented as a probability.

---

# 9. Phase R5 — Stop-loss research

Do not optimize exits until entry/setup behavior has first been understood, but stop behavior should be analyzed before final strategy certification.

Compare the current fixed stop framework with alternatives.

Candidate fixed stops:

```text
15 points
20 points
25 points
30 points
35 points
```

Also compare where supported:

- swing / structure stop;
- sweep-extreme stop;
- volatility-adjusted stop;
- ATR-like stop;
- structure stop with maximum cap.

Key analysis:

- MAE of eventual winners;
- percentage of winners that would survive each stop;
- additional loss size from wider stops;
- expectancy R;
- PF;
- drawdown;
- setup-family differences.

Do not widen stops merely to increase win rate.

---

# 10. Phase R6 — Exit / trade-management experiments

This experiment family was intentionally deferred until after untouched baseline establishment.

The current simulator has historically behaved largely as an all-or-nothing **TP4 vs stop** model while still recording TP1-TP4 touches.

Earlier research showed an important clue: TP1 could be reached by more than half of trades even while headline full-position win rate was around the low-20% range. That makes exit efficiency a high-priority research question.

## Required exit models

### EXIT-A — Current baseline

```text
100% position -> TP4 or stop
```

### EXIT-B — TP1 then break-even runner

```text
Take profit at TP1
Move remaining risk to break-even
Run remainder toward TP4
```

### EXIT-C — Equal partials

```text
25% TP1
25% TP2
25% TP3
25% TP4
```

### EXIT-D — Partial TP1 + break-even

```text
Take partial at TP1
Move remainder to break-even
Continue toward later targets
```

### EXIT-E — 50% TP1 + runner

```text
50% at TP1
remaining 50% -> break-even
runner targets TP4 / structural liquidity
```

## Additional candidates after required models

- TP1 + trailing structure stop;
- TP2 + runner;
- liquidity-target exits instead of fixed points;
- time-based exit;
- MFE-aware trailing logic;
- different management for continuation vs reversal.

## Exit-model evaluation

Compare:

- expectancy points / R;
- PF;
- net points / R;
- maximum drawdown;
- average / median trade;
- average win / loss;
- MFE capture efficiency;
- MAE;
- stop-to-BE conversion rate;
- percentage of TP1 trades that eventually stop;
- percentage of TP2 / TP3 trades that fail to reach TP4;
- yearly robustness.

Do not choose the exit model solely because it has the highest win rate.

---

# 11. Phase R7 — Interaction experiments

Only after individual components are understood should combinations be tested.

Suggested incremental sequence:

```text
Level reaction / break
+ retest
+ volume / RVOL
+ HTF bias
+ sweep context
+ displacement
+ structure shift
+ FVG
+ DOL
+ premium / discount
+ SNR
+ room to target
```

At each addition record:

- incremental expectancy change;
- PF change;
- drawdown change;
- MFE / MAE change;
- trade-count reduction;
- year-by-year stability.

This identifies where additional confirmation stops helping and begins over-filtering.

---

# 12. Phase R8 — Market regime and day-type research

Segment results by conditions such as:

- high volatility;
- low volatility;
- trending;
- ranging / mean reverting;
- high SNR;
- low SNR;
- large overnight range;
- narrow overnight range;
- wide PMH-PML range;
- narrow PMH-PML range;
- gap / no gap;
- news-heavy opening if deterministic event data later becomes available.

Questions:

- Are continuations strongest on trend days?
- Are sweeps strongest on range days?
- Should the system avoid specific regimes entirely?
- Can regime identification happen causally before the trade rather than only after the session?

Never use future day information to classify a trade at entry time.

---

# 13. Phase R9 — Robustness tests

Before accepting a modification, challenge it.

## 13.1 Year-by-year

Candidate should not rely entirely on one historical year.

## 13.2 Month-by-month

Look for a few exceptional months carrying the result.

## 13.3 Long / short

Ensure aggregate gains are not hiding a severely broken direction unless the strategy explicitly excludes it.

## 13.4 Setup family

Check reversal and continuation separately.

## 13.5 Parameter sensitivity

A robust threshold should work reasonably near the chosen value.

Example:

If RVOL 1.51 works brilliantly but 1.45 and 1.60 collapse, treat the result as suspicious.

Prefer broad plateaus of acceptable performance to sharp historical optima.

## 13.6 Slippage / commissions

Re-run final candidates with realistic MNQ costs and slippage assumptions.

A small historical edge that disappears after costs is not production-ready.

## 13.7 Outlier dependence

Report results with and without the largest winners.

Determine whether profitability depends on a handful of extreme trades.

---

# 14. Phase R10 — Held-out and walk-forward validation

No final strategy change is accepted using only the data on which it was developed.

## Minimum structure

Split available history into:

- development / calibration set;
- untouched validation set.

Do not inspect the validation set repeatedly while choosing parameters.

## Preferred structure

Use rolling walk-forward windows.

Example conceptual process:

```text
Train / research on earlier period
-> freeze candidate
-> test on next unseen period
-> roll forward
-> repeat
```

Aggregate performance across unseen windows.

Acceptance requires stability, not one lucky holdout.

---

# 15. Phase R11 — Final candidate comparison

At the end of research, compare at least:

```text
Baseline strategy
Best entry-quality refinement
Best scoring refinement
Best exit model
Combined candidate
```

The combined candidate should only combine changes that independently demonstrated value.

Final report should show:

- baseline vs candidate;
- overall metrics;
- each year;
- each setup family;
- long / short;
- score bands;
- time buckets;
- volatility / SNR regimes;
- drawdown;
- cost-adjusted performance;
- validation / walk-forward performance.

---

# 16. Phase R12 — Production acceptance gates

A candidate strategy may replace the current production configuration only when all applicable gates pass.

## Required gates

- [ ] improvement hypothesis documented before testing
- [ ] baseline comparison complete
- [ ] adequate sample size
- [ ] expectancy improved or preserved with meaningful risk improvement
- [ ] profit factor improved or preserved
- [ ] drawdown acceptable
- [ ] not dependent on a single year
- [ ] not dependent on a handful of outlier winners
- [ ] score bands show useful discrimination
- [ ] no obvious feature double counting
- [ ] reasonable parameter sensitivity
- [ ] realistic transaction costs tested
- [ ] held-out / walk-forward validation passed
- [ ] Phase 11 shadow/live observations do not contradict the historical result
- [ ] final strategy config committed
- [ ] final evidence archived

Do not update live alert thresholds merely because an in-sample backtest improved.

---

# 17. Standard experiment report template

Every formal experiment should produce a record resembling:

```markdown
# EXP-XXX — Name

## Hypothesis
What do we believe will improve and why?

## Baseline
Git SHA:
Config SHA:
Input dataset:
Input SHA:
Years:
Trades:

## Single controlled change
Exactly what changed?

## Overall results
- Trades:
- Win rate:
- Expectancy points:
- Expectancy R:
- Profit factor:
- Net points / R:
- Max drawdown:
- MFE:
- MAE:
- TP1 / TP2 / TP3 / TP4:

## Baseline delta
- Trade-count delta:
- Expectancy delta:
- PF delta:
- Drawdown delta:

## Segmentation
- 2023:
- 2024:
- 2025:
- Long:
- Short:
- Reversal:
- Continuation:
- Score bands:
- Time buckets:

## Robustness
- Parameter neighbors:
- Cost-adjusted:
- Outlier dependence:

## Decision
ACCEPT / REJECT / INVESTIGATE

## Reason
Evidence-based conclusion.
```

---

# 18. Recommended experiment order

Follow this order unless a discovered implementation bug requires interruption.

```text
R0   Freeze / certify untouched baseline

R1   EXP-001 Score-band baseline
     EXP-002 Long vs short
     EXP-003 Reversal vs continuation
     EXP-004 Year / regime decomposition

R2   EXP-005 Level-specific performance
     EXP-006 HTF bias
     EXP-007 Liquidity sweep
     EXP-008 Breakout / acceptance
     EXP-009 Displacement
     EXP-010 MSS / BOS / CHOCH
     EXP-011 FVG / IFVG
     EXP-012 Order blocks
     EXP-013 Premium / discount
     EXP-014 Draw on Liquidity
     EXP-015 Volume / RVOL
     EXP-016 SNR / efficiency
     EXP-017 VWAP
     EXP-018 S/R confluence
     EXP-019 Room to target

R3   EXP-020 Time of day
     EXP-021 Entry confirmation / execution

R4   Score-component lift
     Redundancy analysis
     Weight candidates
     Threshold calibration
     Setup-family score split if justified

R5   Stop-loss research

R6   EXIT-A through EXIT-E

R7   Controlled interaction / confirmation-stack experiments

R8   Regime / day-type research

R9   Robustness / sensitivity / cost tests

R10  Held-out / walk-forward validation

R11  Final candidate comparison

R12  Production acceptance
```

---

# 19. Immediate next steps from the current checkpoint

The infrastructure/data work has progressed far enough to begin actual strategy research.

Do not change the strategy yet.

Next actions:

1. Freeze and archive the corrected three-year baseline.
2. Run **EXP-001 — Score-band baseline analysis** against the existing 2023 / 2024 / 2025 trade ledgers.
3. Confirm whether higher scores currently correspond to better expectancy / PF / TP reach.
4. Run EXP-002 through EXP-004 to locate broad weaknesses before touching weights.
5. Begin component contribution analysis.
6. Only after evidence exists, propose the first scoring-weight or strategy-rule change.
7. Keep exit-model research separate until the baseline component analysis is complete.

The first objective is diagnosis, not optimization.

---

# 20. Guiding principles

1. **Measure before changing.**
2. **Change one family at a time.**
3. **Preserve the untouched baseline forever.**
4. **Do not optimize one year in isolation.**
5. **Do not judge by win rate alone.**
6. **Do not treat confluence score as win probability.**
7. **Reward components according to demonstrated incremental value.**
8. **Penalize redundant double counting.**
9. **Prefer robust parameter ranges over sharp historical optima.**
10. **Validate on unseen data.**
11. **Account for realistic execution costs.**
12. **Keep research evidence reproducible and archived.**
13. **Do not remove legitimate market data merely to make validation warnings disappear.**
14. **The final strategy should be simpler if additional complexity does not add measurable edge.**

The purpose of the research system is not to prove the discretionary framework correct. It is to determine which pieces deserve to survive into the final strategy and how strongly each should influence an actual trade decision.
