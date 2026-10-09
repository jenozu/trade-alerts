# R6.0 — Fixed Full-Target Sweep Review

## Status

Completed full chronological replays for 2023, 2024 and 2025.

This experiment changed only the full-position target distance:

- 50 points
- 75 points
- 100 points (frozen control)

All non-target behavior remained frozen:

- baseline score weights;
- threshold-70 eligibility;
- setup and entry logic;
- current structural/25-point-fallback stop logic;
- time/session rules;
- one-open-trade behavior;
- slippage assumptions;
- maximum holding time.

The 100-point control reproduced the frozen baseline trade-for-trade in all three years:

- 2023: 344 trades
- 2024: 388 trades
- 2025: 486 trades

## Year-by-year results

| Year | Full TP | Trades | Win rate | Net points | Expectancy | PF | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2023 | 50 | 384 | 39.32% | +1102.25 | +2.8704 | 1.1899 | 540.75 |
| 2023 | 75 | 361 | 33.52% | +1020.25 | +2.8262 | 1.1715 | 655.50 |
| 2023 | 100 | 344 | 32.27% | +1003.00 | +2.9157 | 1.1749 | 545.50 |
| 2024 | 50 | 412 | 34.22% | -268.00 | -0.6505 | 0.9603 | 908.75 |
| 2024 | 75 | 398 | 29.15% | -27.00 | -0.0678 | 0.9961 | 982.75 |
| 2024 | 100 | 388 | 27.32% | +66.25 | +0.1707 | 1.0095 | 1091.75 |
| 2025 | 50 | 528 | 35.42% | +617.25 | +1.1690 | 1.0728 | 558.50 |
| 2025 | 75 | 501 | 26.95% | +70.75 | +0.1412 | 1.0078 | 752.25 |
| 2025 | 100 | 486 | 24.90% | +1103.25 | +2.2701 | 1.1220 | 758.50 |

## Combined descriptive totals

These totals are descriptive sums across the three independently replayed research years.

| Full TP | Trades | Wins | Win rate | Net points | Net/trade |
| --- | ---: | ---: | ---: | ---: | ---: |
| 50 | 1324 | 479 | 36.18% | +1451.50 | +1.0963 |
| 75 | 1260 | 372 | 29.52% | +1064.00 | +0.8444 |
| 100 | 1218 | 338 | 27.75% | +2172.50 | +1.7837 |

A pooled PF or pooled max drawdown is intentionally not reconstructed from annual summaries; those require the underlying chronological trade ledgers.

## Interpretation

The 50-point full exit materially increased win rate and shortened exposure, and it reduced the worst observed annual drawdown relative to the 100-point control. It was competitive in 2023.

However, it did not improve the strategy consistently:

- 2024 turned from +66.25 at TP100 to -268.00 at TP50.
- 2025 fell from +1103.25 at TP100 to +617.25 at TP50.
- Combined net points and expectancy per trade remained materially stronger at TP100.

The 75-point full exit did not provide a compelling middle ground. It underperformed TP100 in combined net points and expectancy and remained negative in 2024.

## Decision

**KEEP 100-POINT FULL EXIT AS THE CURRENT CONTROL — DO NOT CHANGE PRODUCTION.**

The R6.0 result does not support replacing TP100 with a full TP50 or TP75 exit.

The TP50 behavior is still useful evidence: it produced a substantially higher win rate and often lower drawdown. This supports testing **partial realization / runner management** rather than closing the entire position at 50.

## Next experiment

Continue within the existing R6 exit-management family.

Do not repeat the 50/75/100 fixed-target sweep under different score models yet; that would mix scoring calibration with exit research and create redundant comparisons.

Next isolate exit management while keeping entry, scoring, stop logic and the 100-point runner target frozen.
