# EXP-002 — Long vs Short

Status: Complete

## Question

Does the current strategy exhibit meaningful and stable directional asymmetry between LONG and SHORT trades, and where does that asymmetry come from?

## Control

Untouched completed annual baselines for 2023, 2024, and 2025. EXP-002 is diagnostic only.

No score weights, entry logic, stop logic, exit logic, setup qualification, or long/short configuration split was changed.

## Inputs

- 2023 ledger: `/docker/trade-alerts-2023/data/results/backtest/trades.csv`
- 2024 ledger: `/docker/trade-alerts-2024/data/results/backtest/trades.csv`
- 2025 ledger: `/docker/trade-alerts/data/results/research_runs/2025_pipeline_final/backtest/trades.csv`

The 20-stage pipelines were not rerun.

## Implementation

- Analyzer: `src/directional_research.py`
- Runner: `scripts/run_exp002_long_vs_short.py`
- Tests: `tests/test_directional_research.py`
- VPS outputs: `data/reports/EXP-002_long-vs-short/`
- Generated artifacts: `EXP-002_long-vs-short.md`, `exp002_long_vs_short_results.json`, `directional_metrics.csv`

## Overall direction comparison

| Direction | Trades | Win rate | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Med MFE | Avg MAE | Med MAE | Avg hold |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| LONG | 653 | 29.9% | +2.94 | +0.118 | 1.17 | +1917.50 | 47.5% | 34.2% | 22.4% | 13.8% | 68.3% | 39.81 | 23.75 | 27.30 | 27.25 | 20.25 |
| SHORT | 565 | 25.3% | +0.45 | +0.017 | 1.02 | +255.00 | 46.7% | 31.2% | 21.2% | 15.6% | 73.1% | 39.07 | 21.25 | 26.80 | 27.50 | 16.35 |

Long-minus-short expectancy gap: **+2.49 points/trade**.

The aggregate result strongly favors longs, but the asymmetry is not stable in sign across all three years.

## Year-by-year

| Year | Direction | Trades | Win rate | Exp pts | Exp R | PF | Net pts |
|---|---|---:|---:|---:|---:|---:|---:|
| 2023 | LONG | 181 | 32.0% | +2.33 | +0.093 | 1.14 | +422.00 |
| 2023 | SHORT | 163 | 32.5% | +3.56 | +0.144 | 1.21 | +581.00 |
| 2024 | LONG | 221 | 29.9% | +1.50 | +0.061 | 1.09 | +332.50 |
| 2024 | SHORT | 167 | 24.0% | -1.59 | -0.063 | 0.91 | -266.25 |
| 2025 | LONG | 251 | 28.3% | +4.63 | +0.186 | 1.26 | +1163.00 |
| 2025 | SHORT | 235 | 21.3% | -0.25 | -0.013 | 0.99 | -59.75 |

Interpretation:

- 2023 contradicts a universal long advantage: shorts were stronger than longs.
- 2024 and 2025 show clear long superiority, with shorts negative in both years.
- The aggregate direction gap has the long-favoring sign in **2 of 3 years**, so the asymmetry is meaningful but not yet robust enough to justify separate production scoring.

## Score-band performance

| Band | Direction | Trades | Win rate | Exp pts | Exp R | PF | Net pts |
|---|---|---:|---:|---:|---:|---:|---:|
| 70–79 | LONG | 509 | 29.7% | +1.67 | +0.068 | 1.10 | +851.25 |
| 70–79 | SHORT | 449 | 25.4% | -0.14 | -0.007 | 0.99 | -63.25 |
| 80–89 | LONG | 131 | 30.5% | +7.52 | +0.297 | 1.43 | +984.75 |
| 80–89 | SHORT | 108 | 23.1% | +1.04 | +0.042 | 1.05 | +112.00 |
| 90–100 | LONG | 13 | 30.8% | +6.27 | +0.251 | 1.36 | +81.50 |
| 90–100 | SHORT | 8 | 50.0% | +25.78 | +1.031 | 3.04 | +206.25 |

The 70–79 and 80–89 samples reinforce [[../Findings/F004-Long-Short-Score-Asymmetry]]. High-scoring shorts are not uniformly poor, but the 80–89 short cohort is only marginally positive while equally scored longs are much stronger. The 90–100 short result is promising but has only eight trades and cannot be trusted as evidence of calibration quality.

## Score distribution

- LONG: n=653, mean 76.11, median 74.42, standard deviation 5.45.
- SHORT: n=565, mean 75.36, median 73.59, standard deviation 5.11.

The directional score distributions are very similar despite the large outcome difference. This is evidence that equal numeric scores do not currently imply equal realized quality across directions.

## Context diagnostics

### HTF alignment

- Aligned LONG: n=608, +3.36 expectancy, PF 1.20.
- Aligned SHORT: n=511, +0.73 expectancy, PF 1.04.
- Neutral/unknown LONG: n=45, -2.73 expectancy, PF 0.85.
- Neutral/unknown SHORT: n=54, -2.22 expectancy, PF 0.88.

HTF alignment helps both directions, but it does not eliminate the directional gap.

### Liquidity sweep

- Sweep present LONG: n=578, +3.12 expectancy, PF 1.18.
- Sweep present SHORT: n=455, -1.60 expectancy, PF 0.91.
- Sweep absent LONG: n=75, +1.51 expectancy, PF 1.09.
- Sweep absent SHORT: n=110, +8.94 expectancy, PF 1.52.

This is a large short-side inversion and is recorded separately in [[../Findings/F007-Short-Liquidity-Sweep-Weakness]]. It is preliminary until EXP-007 decomposes sweep direction and sequencing by year/context.

### Displacement

- Displacement present LONG: n=466, +5.52 expectancy, PF 1.33.
- Displacement present SHORT: n=424, +0.95 expectancy, PF 1.05.
- Displacement absent LONG: n=187, -3.49 expectancy, PF 0.81.
- Displacement absent SHORT: n=141, -1.04 expectancy, PF 0.94.

Displacement is positively discriminative in both directions, more strongly for longs.

### Structure shift

- Structure shift present LONG: n=437, +4.66 expectancy, PF 1.27.
- Structure shift present SHORT: n=401, +1.60 expectancy, PF 1.09.
- Structure shift absent LONG: n=216, -0.55 expectancy, PF 0.97.
- Structure shift absent SHORT: n=164, -2.36 expectancy, PF 0.88.

Structure shift is also positively discriminative in both directions.

### FVG context

- FVG present LONG: n=93, +7.40 expectancy, PF 1.45.
- FVG present SHORT: n=82, +8.48 expectancy, PF 1.50.
- FVG absent LONG: n=560, +2.19 expectancy, PF 1.13.
- FVG absent SHORT: n=483, -0.91 expectancy, PF 0.95.

FVG context is one of the strongest aggregate short-side separators observed in EXP-002. This remains preliminary until the dedicated FVG experiment tests year stability and FVG subtype/sequence.

### DOL / HTF-bias representation

The ledger's categorical `htf_bias` and `dol_direction` fields are almost direction-exclusive: bullish categories contain essentially longs and bearish categories essentially shorts. They therefore do not support a clean same-category long-vs-short comparison. The derived `htf_alignment` result above is more interpretable for EXP-002.

### SNR / RVOL

Raw directional distributions were similar:

- SNR 1m mean: LONG 1.94 vs SHORT 1.90.
- SNR 5m mean: LONG 1.79 vs SHORT 1.61.
- SNR 15m mean: LONG 1.97 vs SHORT 2.11.
- rolling RVOL mean: LONG 2.63 vs SHORT 2.71.
- time-of-day RVOL mean: LONG 1.40 vs SHORT 1.39.

The aggregate long/short gap is therefore not obviously explained by a large unconditional SNR or RVOL distribution difference. Threshold/regime effects still require EXP-015 and EXP-016.

### Time of day

The generated time-bucket output placed all 1,218 trades into `10:30+`. That is not a useful segmentation of the intended 09:30–10:30 ET research window, so EXP-002 makes **no time-of-day directional claim** from this field. EXP-020 must verify timestamp/timezone semantics before using time buckets for strategy decisions.

## Answers to EXP-002 questions

1. **Are longs materially stronger or weaker overall?** Stronger overall: +2.94 expectancy / PF 1.17 versus shorts +0.45 / PF 1.02.
2. **Is the difference stable across 2023–2025?** No. Shorts were stronger in 2023; longs were materially stronger in 2024 and 2025.
3. **Is one direction only weak in certain score bands?** Short weakness is concentrated heavily in the large 70–79 band and remains much weaker than longs at 80–89. The 90–100 sample is too small.
4. **Is one direction weak only in certain regimes/context?** Context matters substantially. Sweep-present shorts are weak, while FVG-present, displacement-present, structure-shift-present, and HTF-aligned shorts are positive.
5. **Are high-scoring shorts genuinely high quality?** The 80–89 short cohort is only marginally positive; the apparently excellent 90–100 cohort has only eight trades. Current evidence does not establish reliable high-score short quality.
6. **Are score distributions materially different?** No. Means/medians are close despite materially different outcomes.
7. **Is one scoring model equally calibrated for both directions?** The evidence says no: comparable scores produce much stronger realized expectancy for longs in the two large score bands.
8. **Enough evidence for separate long/short scoring later?** Enough to make separate directional calibration a formal candidate for later scoring research, but not enough to implement it now because year stability is missing.
9. **Which differences are too small/sample-limited to trust?** The 90–100 cohorts, tiny neutral/opposed DOL/HTF cells, and the unusable time bucket must not drive decisions.

## Evidence classification

### Strong / supported

- Aggregate longs materially outperform shorts across 1,218 trades.
- The large 70–79 and 80–89 bands show materially better long expectancy/PF than short expectancy/PF.
- Long and short raw score distributions are similar despite different realized quality.
- HTF alignment, displacement, and structure shift improve both directions at aggregate scale.

### Preliminary

- The long advantage is not universal because 2023 favored shorts.
- Sweep-present shorts appear structurally weak relative to sweep-absent shorts.
- FVG context appears especially important for short quality.
- The 90–100 short cohort appears excellent but has only eight trades.
- Time-of-day behavior is unresolved because the current timestamp bucket did not meaningfully segment the sample.

## Decision

**INVESTIGATE — no strategy change.**

EXP-002 supports treating long/short calibration as a later research candidate, but does **not** authorize separate score weights, separate configs, or changes to entry/stop/exit logic. Directional asymmetry must be decomposed further by setup family and regime before any scoring split is considered.

## Findings

- [[../Findings/F004-Long-Short-Score-Asymmetry]]
- [[../Findings/F005-Year-Regime-Dependence]]
- [[../Findings/F007-Short-Liquidity-Sweep-Weakness]]
- [[../Findings/F008-FVG-Context-Concentrates-Short-Edge]]
- [[../Findings/F009-Similar-Scores-Different-Directional-Quality]]

## Next

The exact next experiment from `refine-roadmap.md` is **EXP-003 — Setup-family comparison (Reversal vs Continuation)**. Do not start it yet.
