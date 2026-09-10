# EXP-003 — Setup Family Comparison

Status: Complete — diagnostic only

Date: 2026-09-10

## Objective

Compare the two production setup-family labels used by the strategy:

1. Liquidity Sweep → Reversal
2. Break → Retest → Continuation

No score weights, entries, stops, targets, or production configuration were changed.

## Data

EXP-003 used the existing completed trade ledgers only. The 20-stage historical pipelines were not rerun.

- 2023: `/docker/trade-alerts-2023/data/results/backtest/trades.csv`
- 2024: `/docker/trade-alerts-2024/data/results/backtest/trades.csv`
- 2025: `/docker/trade-alerts/data/results/research_runs/2025_pipeline_final/backtest/trades.csv`

Combined sample: **1,218 trades**.

## Family classification contract

The archived `trades.csv` files do not persist an explicit setup-family field.

The existing production planner classifies a directional candidate as `reversal` when directional reversal/liquidity-sweep context exists and otherwise as `continuation`. The historical backtester persists the same directionally aligned recent sweep state as `liquidity_sweep`.

Therefore the ledger-only EXP-003 analyzer uses the deterministic projection:

- `liquidity_sweep=True` → `reversal`
- `liquidity_sweep=False` → `continuation`

This is a projection of the existing planner family-selection contract, not a newly invented heuristic. It does **not** prove that every continuation-bucket trade completed the full production acceptance → retest → BOS sequence; those richer sequence fields are not present in the archived trade ledgers.

## Overall performance

| Family | Trades | Win rate | Expectancy pts | Expectancy R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Med MFE | Avg MAE | Med MAE | Avg hold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Reversal | 1,033 | 27.2% | +1.04 | +0.042R | 1.06 | +1,076.25 | 46.1% | 32.4% | 21.2% | 13.6% | 71.0% | 38.71 | 22.00 | 27.23 | 27.50 | 18.72 |
| Continuation | 185 | 30.8% | +5.93 | +0.234R | 1.34 | +1,096.25 | 53.0% | 34.6% | 25.4% | 20.5% | 68.1% | 43.70 | 28.75 | 26.17 | 27.00 | 16.83 |

Continuation outperformed reversal by approximately **+4.89 expectancy points per trade** despite comprising only 15.2% of the sample.

## Year-by-year stability

| Year | Family | Trades | Win rate | Exp pts | Exp R | PF | Net pts |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2023 | Reversal | 298 | 32.2% | +2.79 | +0.113R | 1.17 | +830.00 |
| 2023 | Continuation | 46 | 32.6% | +3.76 | +0.146R | 1.22 | +173.00 |
| 2024 | Reversal | 328 | 25.6% | -1.61 | -0.063R | 0.91 | -526.50 |
| 2024 | Continuation | 60 | 36.7% | +9.88 | +0.391R | 1.63 | +592.75 |
| 2025 | Reversal | 407 | 24.8% | +1.90 | +0.075R | 1.10 | +772.75 |
| 2025 | Continuation | 79 | 25.3% | +4.18 | +0.167R | 1.22 | +330.50 |

Continuation had higher expectancy and PF in **all three years**. The size of the advantage varied substantially; 2024 produced the largest separation.

## Direction within setup family

| Segment | Trades | Exp pts | Exp R | PF | Net pts |
| --- | ---: | ---: | ---: | ---: | ---: |
| LONG reversal | 578 | +3.12 | +0.126R | 1.18 | +1,804.50 |
| LONG continuation | 75 | +1.51 | +0.056R | 1.09 | +113.00 |
| SHORT reversal | 455 | -1.60 | -0.064R | 0.91 | -728.25 |
| SHORT continuation | 110 | +8.94 | +0.356R | 1.52 | +983.25 |

The family comparison is highly direction-dependent. Long reversals were stronger than long continuations, while short continuations were dramatically stronger than short reversals.

This strengthens [[../Findings/F007-Short-Liquidity-Sweep-Weakness]].

## Score distribution and score-band performance

Mean/median scores:

- Reversal: mean **76.22**, median **74.58**, n=1,033.
- Continuation: mean **73.24**, median **71.82**, n=185.

Score-band counts:

- Reversal: 70–79 n=798; 80–89 n=214; 90–100 n=21.
- Continuation: 70–79 n=160; 80–89 n=25; 90–100 n=0.

Performance:

| Score band | Family | Trades | Exp pts | PF | Net pts |
| --- | --- | ---: | ---: | ---: | ---: |
| 70–79 | Reversal | 798 | +0.11 | 1.01 | +90.75 |
| 70–79 | Continuation | 160 | +4.36 | 1.25 | +697.25 |
| 80–89 | Reversal | 214 | +3.26 | 1.18 | +697.75 |
| 80–89 | Continuation | 25 | +15.96 | 1.99 | +399.00 |
| 90–100 | Reversal | 21 | +13.70 | 1.88 | +287.75 |
| 90–100 | Continuation | 0 | — | — | — |

The current shared score appears materially miscalibrated by family: continuation trades receive lower scores on average yet realize much stronger expectancy. Reversal performance is essentially flat in 70–79 and improves materially from 80 upward. Continuations were already profitable in 70–79, but the 80–89 continuation sample is only 25 trades and must remain exploratory.

See [[../Findings/F010-Shared-Score-Miscalibrated-By-Setup-Family]].

## Context diagnostics

### Displacement

- Reversal without displacement: n=298, **-3.43 pts**, PF **0.82**.
- Reversal with displacement: n=735, **+2.85 pts**, PF **1.16**.
- Continuation without displacement: n=30, **+7.37 pts**, PF **1.42**.
- Continuation with displacement: n=155, **+5.65 pts**, PF **1.33**.

Displacement strongly separates reversal quality in this ledger representation. The 30 no-displacement continuation trades are exploratory and should not be interpreted as evidence that displacement is unnecessary for the production continuation sequence.

### FVG context

- Reversal without FVG context: n=870, **-0.19 pts**, PF **0.99**.
- Reversal with FVG context: n=163, **+7.63 pts**, PF **1.46**.
- Continuation without FVG context: n=173, **+5.53 pts**, PF **1.32**.
- Continuation with FVG context: n=12, **+11.65 pts**, PF **1.69**.

FVG context is a strong discriminator inside the reversal bucket. The continuation+FVG cell has only 12 trades and is preliminary.

See [[../Findings/F011-Reversal-Quality-Depends-On-Confirmation-Context]].

### HTF alignment

- HTF-aligned reversal: n=940, +1.39 pts, PF 1.08.
- HTF-aligned continuation: n=179, +6.21 pts, PF 1.36.
- Neutral/unknown reversal: n=93, -2.44 pts, PF 0.87.
- Neutral/unknown continuation: n=6, -2.67 pts, PF 0.86.

Both families benefited from alignment. The neutral/unknown continuation sample is too small for a stable family conclusion.

### SNR / RVOL

Unconditional means/medians:

- SNR 1m: reversal 1.83 / 1.73; continuation 2.44 / 2.28.
- SNR 5m: reversal 1.61 / 1.37; continuation 2.26 / 2.14.
- SNR 15m: reversal 1.91 / 1.59; continuation 2.74 / 2.50.
- rolling RVOL: reversal 2.64 / 1.72; continuation 2.83 / 1.78.
- time-of-day RVOL: reversal 1.37 / 1.28; continuation 1.53 / 1.50.

Continuation trades occurred in materially higher-SNR conditions on average. RVOL differences were smaller. These are descriptive associations, not causal thresholds; EXP-015 and EXP-016 remain the dedicated component experiments.

## 2024 diagnosis

EXP-003 provides a strong explanation for much of the weak 2024 baseline:

- Reversal: **328 trades, -1.61 pts expectancy, PF 0.91, -526.50 net points**.
- Continuation: **60 trades, +9.88 pts expectancy, PF 1.63, +592.75 net points**.

The near-flat overall 2024 result was therefore not broad weakness across both setup families. It was heavily concentrated in the reversal-classified majority while the smaller continuation bucket performed strongly.

This strengthens [[../Findings/F005-Year-Regime-Dependence]].

## Unsupported dimensions / limitations

The archived trade ledgers do not separately expose:

- level type;
- explicit volatility regime;
- acceptance detail;
- retest-quality detail;
- BOS as a separate field;
- MSS/CHOCH as separate fields.

The available timestamp representation also collapses the EXP-003 report into the same `10:30+` bucket observed in EXP-002, so no valid time-of-day conclusion is made here.

Therefore EXP-003 cannot truthfully answer whether continuations specifically require acceptance, retest quality, or BOS, nor whether reversals specifically require MSS versus CHOCH. Those questions must use richer scored/structure artifacts in the later component experiments.

The family proxy also means that `continuation` identifies the planner's non-reversal family choice from the archived ledger, not independently verified completion of every production continuation state-machine step.

## Answers to EXP-003 questions

1. **Which family is stronger overall?** Continuation, materially: +5.93 pts / PF 1.34 versus reversal +1.04 / PF 1.06.
2. **Stable across years?** Yes in direction: continuation had higher expectancy and PF in 2023, 2024, and 2025, although the magnitude varied greatly.
3. **Direction dependence?** Yes. Long reversals outperformed long continuations, while short continuations dramatically outperformed short reversals.
4. **Higher-score requirement?** Reversals appear to require stronger score context: 70–79 was near breakeven while 80–89 was materially better. Continuations were already profitable in 70–79. This supports later family-specific threshold research, not an immediate threshold change.
5. **Reversal dependencies?** Displacement and FVG context strongly discriminate reversal quality. Separate MSS/CHOCH cannot be tested from these ledgers.
6. **Continuation dependencies?** HTF-aligned continuations were strong, but acceptance, retest quality, and BOS are not separately persisted and cannot be truthfully isolated here.
7. **2024 weakness?** Yes. Reversal trades lost 526.50 points while continuations gained 592.75 points.
8. **Shared scorer miscalibration?** Supported diagnostically: continuation has lower average scores but much higher realized expectancy, especially inside the same 70–79 band.
9. **Separate scoring/thresholds later?** There is enough evidence to justify dedicated family-specific calibration research later. There is **not** enough evidence to change production weights, thresholds, or configs now.

## Evidence strength

### Strong / supported

- Continuation outperformed reversal overall.
- Continuation had higher expectancy/PF in each of 2023, 2024, and 2025.
- 2024 weakness was concentrated in reversals while continuations remained strong.
- Short reversal versus short continuation performance is sharply asymmetric.
- Shared score calibration differs materially by family.
- Reversal quality is strongly associated with displacement and FVG context.

### Preliminary / sample-limited

- Continuation 80–89 performance: only 25 trades.
- Continuation+FVG: only 12 trades.
- Neutral/unknown HTF continuation: only 6 trades.
- Reversal 90–100: only 21 trades.
- Any inference that continuation does not require displacement is unsupported because the no-displacement continuation cell has only 30 trades and the ledger family proxy does not encode the full continuation state machine.

## Decision

**INVESTIGATE — no strategy change.**

EXP-003 supports later research into family-specific scoring and thresholds, but does not authorize production separation yet. No validated decision is added under `trade-brain/30-Decisions/`.

## Related findings

- [[../Findings/F005-Year-Regime-Dependence]]
- [[../Findings/F007-Short-Liquidity-Sweep-Weakness]]
- [[../Findings/F010-Shared-Score-Miscalibrated-By-Setup-Family]]
- [[../Findings/F011-Reversal-Quality-Depends-On-Confirmation-Context]]
