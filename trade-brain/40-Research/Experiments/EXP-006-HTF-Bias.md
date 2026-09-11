# EXP-006 — HTF Bias

Status: Complete — diagnostic only

Sources:
- `research-archive/EXP-006/EXP-006-HTF-Bias.md`
- `research-archive/EXP-006/exp006_htf_bias_results.json`
- `research-archive/EXP-006/htf_bias_metrics.csv`

Related findings:
- [[../Findings/F005-Year-Regime-Dependence]]
- [[../Findings/F018-HTF-Composite-Conflict-Is-Not-A-Universal-Filter]]
- [[../Findings/F019-1H-and-15M-Bias-Carry-More-Useful-Directional-Signal-Than-30M]]
- [[../Findings/F020-HTF-Scoring-Is-Selection-Confounded-In-Baseline-Trades]]

## Objective

Determine how higher-timeframe bias affects trade quality, which individual timeframe appears most informative, whether multiple HTF inputs are redundant, and whether current HTF scoring is supported by the untouched 2023–2025 baseline.

## Method

The 1,218 baseline trades were joined at exact signal time to the already-verified scored feature artifacts. No historical pipeline was rerun. The production intraday composite uses 1H/30m/15m weighted 3/2/1; macro context uses 4H/1D weighted 2/1. The current scorer awards +10 points for composite alignment and applies -20 for composite directional conflict.

## Coverage

- Matched feature rows: 1,218 / 1,218 (100%).
- Time-of-day data remained degenerate in the baseline ledger and was not used for conclusions.

## Headline production HTF context

- Aligned: 803 trades, +1.86 pts expectancy, +0.074R, PF 1.10, +1,491.75 points.
- Conflicting: 415 trades, +1.64 pts expectancy, +0.066R, PF 1.09, +680.75 points.

The aggregate difference is small. Component conflict by itself is therefore not a strong universal exclusion signal in the already-selected baseline trades.

## Cross-year behavior

- 2023 aligned: +2.23 / PF 1.13; conflicting: +3.90 / PF 1.23.
- 2024 aligned: -0.81 / PF 0.96; conflicting: +2.29 / PF 1.13.
- 2025 aligned: +3.74 / PF 1.21; conflicting: -1.00 / PF 0.95.

This is strongly regime-dependent and strengthens [[../Findings/F005-Year-Regime-Dependence]].

## Setup-family interaction

- Continuation aligned: 142 trades, +5.35 / PF 1.31.
- Continuation conflicting: 43 trades, +7.81 / PF 1.47.
- Reversal aligned: 661 trades, +1.11 / PF 1.06.
- Reversal conflicting: 372 trades, +0.93 / PF 1.05.

The baseline does not show continuations being more dependent on the headline composite-aligned state. Both continuation buckets remained profitable, and conflicting continuations were stronger in this selected sample.

## Direction interaction

- Long aligned: +3.25 / PF 1.19; long conflicting: +2.36 / PF 1.13.
- Short aligned: +0.30 / PF 1.02; short conflicting: +0.76 / PF 1.04.

HTF context does not explain the previously observed long/short asymmetry by itself.

## Individual timeframe diagnostics

Aligned-minus-known-non-aligned expectancy lift:

- 1H: **+5.18 pts/trade**.
- 15m: **+2.52**.
- 4H: **+1.94**.
- 1D: **+1.14**.
- 30m: **-5.56**.

The 1H relation was especially discriminating: 1,169 aligned trades produced +1.99 / PF 1.11 versus 49 opposed trades at -3.18 / PF 0.84. The 15m relation was also positive: +2.41 / PF 1.14 aligned versus -0.12 / PF 0.99 opposed.

The 30m relation moved the opposite way: 1,103 aligned trades produced +1.26 / PF 1.07, while 115 opposed trades produced +6.82 / PF 1.42. This should not be interpreted as causal evidence to invert 30m bias; it is a diagnostic signal requiring controlled ablation.

## Redundancy

The strongest pairwise state agreement was 1H vs 30m at 86.5%, followed by 30m vs 15m at 74.1% and 1H vs 15m at 71.3%. This supports a later redundancy/ablation test rather than simply awarding independent points to each timeframe.

## Score interaction and selection warning

The current baseline contains no pure composite-opposed trades: the pure intraday relation was 1,119 aligned, 99 neutral, and 0 opposed. Since the scorer already gives +10 for alignment and -20 for opposition, the surviving baseline sample is selection-conditioned on HTF scoring.

Within score bands, conflicting trades can look unusually strong—for example 80–89 conflicting produced +16.73 / PF 2.11 versus aligned -0.64 / PF 0.97. That does **not** prove the HTF penalty is wrong; trades that remain high-scoring despite conflict necessarily carry unusually strong other components. A controlled score-component ablation is required before changing the HTF weight.

## Strong evidence

- Exact HTF feature coverage is complete.
- 1H and 15m directional relations show useful positive discrimination in the selected baseline.
- Headline composite conflict is not a universal no-trade filter; its performance changes materially by year.
- 1H/30m state agreement is high enough to raise a real redundancy question.

## Preliminary evidence

- 30m opposition outperformed 30m alignment, but this is observational and may reflect interaction/selection effects.
- 4H and Daily show smaller positive alignment lift than 1H/15m.
- Score-band × HTF results are heavily selection-conditioned and should not be used directly to reweight the scorer.

## Decision

**INVESTIGATE — no strategy change.**

EXP-006 does not justify changing HTF weights, removing the conflict penalty, inverting 30m bias, or adding a new HTF hard filter. Controlled ablation and later held-out validation are required first.

Next experiment: **EXP-007 — Liquidity sweep contribution**.
