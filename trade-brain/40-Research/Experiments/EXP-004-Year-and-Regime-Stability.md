# EXP-004 — Year and Regime Stability

Status: Complete — diagnostic only

Sources:
- `research-archive/EXP-004/EXP-004-Year-and-Regime-Stability.md`
- `research-archive/EXP-004/exp004_year_regime_results.json`
- `research-archive/EXP-004/year_regime_metrics.csv`

Related findings:
- [[../Findings/F001-Score-Expectancy-Ordering]]
- [[../Findings/F005-Year-Regime-Dependence]]
- [[../Findings/F007-Short-Liquidity-Sweep-Weakness]]
- [[../Findings/F010-Shared-Score-Miscalibrated-By-Setup-Family]]
- [[../Findings/F013-Displacement-and-FVG-Are-Cross-Year-Stable-Confirmations]]
- [[../Findings/F014-2024-Weakness-Was-Lower-Favorable-Excursion-Not-Higher-Adverse-Excursion]]

## Objective

Determine why baseline performance changed across 2023, 2024, and 2025, with special focus on the nearly breakeven 2024 baseline, without changing strategy parameters or rerunning the historical pipeline.

## Inputs

Existing completed trade ledgers only:

- 2023: `/docker/trade-alerts-2023/data/results/backtest/trades.csv`
- 2024: `/docker/trade-alerts-2024/data/results/backtest/trades.csv`
- 2025: `/docker/trade-alerts/data/results/research_runs/2025_pipeline_final/backtest/trades.csv`

## Overall year comparison

| Year | Trades | Win rate | Exp pts | Exp R | PF | Net pts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2023 | 344 | 32.3% | +2.92 | +0.117R | 1.17 | +1003.00 |
| 2024 | 388 | 27.3% | +0.17 | +0.007R | 1.01 | +66.25 |
| 2025 | 486 | 24.9% | +2.27 | +0.090R | 1.12 | +1103.25 |

Relative to the mean of 2023 and 2025, 2024 lost about 2.42 expectancy points/trade and 0.139 of profit factor.

## What deteriorated in 2024

The weakness was concentrated rather than universal.

- Reversal: 328 trades, -1.61 pts expectancy, PF 0.91, -526.50 net points.
- Continuation: 60 trades, +9.88 pts expectancy, PF 1.63, +592.75 net points.
- Long: +1.50 pts expectancy, PF 1.09.
- Short: -1.59 pts expectancy, PF 0.91.
- 70–79: -0.24 pts expectancy, PF 0.99.
- 80–89: +3.41 pts expectancy, PF 1.18.

Thus, 2024 weakness was primarily reversal- and short-side weakness, with the largest score band (70–79) failing to contribute edge.

## Target capture and excursions

2024 TP reach was lower than the peer-year mean at every recorded target:

- TP1: 44.3% vs peer mean 48.9%.
- TP2: 30.9% vs 33.8%.
- TP3: 20.9% vs 22.1%.
- TP4: 12.6% vs 15.0%.

The strongest excursion change was reduced favorable movement rather than increased adverse movement:

- Avg MFE: 36.95 vs peer mean 40.51.
- Median MFE: 20.50 vs 25.06.
- Avg MAE: 25.75 vs peer mean 27.21.
- Median MAE: 27.00 vs 27.81.

This indicates poorer opportunity/extension in 2024 more than unusually worse adverse excursion.

## Stable components

Two confirmation features were positive and directionally useful in every year:

- Displacement present: 2023 +4.07 / PF 1.24; 2024 +2.41 / PF 1.14; 2025 +3.58 / PF 1.19.
- FVG context present: 2023 +11.21 / PF 1.71; 2024 +6.56 / PF 1.40; 2025 +6.54 / PF 1.37.

By contrast, displacement-absent trades were negative in all three years.

Structure shift was less stable: structure-shift-absent trades were strong in 2023 but weak in 2024 and 2025.

## SNR / RVOL

Unconditional SNR and RVOL averages did not show a simple 2024 collapse. In several measures, 2024 was similar to or above 2023. Therefore EXP-004 does not support blaming the 2024 weakness on a broad reduction in SNR or RVOL alone.

## HTF context

HTF-aligned trades remained positive in all three years, although 2024 was much weaker (+0.53 / PF 1.03) than 2023 (+2.95 / PF 1.18) and 2025 (+2.89 / PF 1.16).

Neutral/unknown HTF context deteriorated after 2023 and was negative in 2024 and 2025.

## Score-band regime dependence

Score behavior was not stable year to year:

- 70–79: +3.62 in 2023, -0.24 in 2024, -0.28 in 2025.
- 80–89: -0.67 in 2023, +3.41 in 2024, +10.00 in 2025.
- 90–100 remains too small for reliable year-level conclusions: only 3, 5, and 13 trades.

This strengthens the interpretation that the score is ordinal in aggregate but not uniformly calibrated across regimes.

## Limitations

- The archived ledgers do not contain a valid explicit volatility-regime classification.
- All 1,218 trades fall into the available `10:30+` time bucket, so no valid time-of-day conclusion can be drawn from these ledgers.
- Some interesting score/family/direction intersections are sample-limited and require dedicated component experiments.
- EXP-004 is decomposition only; it does not test a changed rule out of sample.

## Conclusion

Strong evidence:

- 2024 weakness was concentrated in reversal-classified and short trades rather than being a universal strategy breakdown.
- Continuation trades remained profitable in every year and were especially strong in 2024.
- Displacement-present and FVG-present trades were positive in all three years.
- 2024 had weaker favorable excursion and target capture than peer years without a corresponding increase in MAE.

Preliminary / nuanced evidence:

- The shared score is regime-sensitive: the 70–79 and 80–89 bands change relative quality across years.
- HTF alignment helps preserve positive expectancy, but its edge magnitude is regime-dependent.
- Structure shift is useful in aggregate but is not uniformly discriminative across every year.

Decision: **INVESTIGATE — no strategy change**.

EXP-004 does not justify changing score weights, entries, stops, targets, or setup logic. The next stage should isolate individual component contributions using the roadmap order.
