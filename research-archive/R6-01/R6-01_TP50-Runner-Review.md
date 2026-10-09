# R6.1 — TP50 Partial Realization + TP100 Runner Review

## Status

Completed full chronological replays for 2023, 2024 and 2025.

The frozen TP100 control passed exact trade-ledger parity in all three years:

- 2023: 344 trades
- 2024: 388 trades
- 2025: 486 trades

Models reviewed:

1. `p50_runner` — 50% exits at +50 points; remaining 50% targets +100; original stop remains.
2. `p50_be_runner` — 50% exits at +50 points; remaining 50% targets +100; runner moves to break-even beginning on the next bar.

No production settings were changed.

## Year-by-year results

| Year | Model | Trades | Net points | Expectancy | PF | Max DD |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2023 | TP100 control | 344 | +1003.00 | +2.9157 | 1.1749 | 545.50 |
| 2023 | p50_runner | 344 | +972.25 | +2.8263 | 1.1869 | 417.62 |
| 2023 | p50_be_runner | 352 | +998.25 | +2.8359 | 1.1873 | 478.62 |
| 2024 | TP100 control | 388 | +66.25 | +0.1707 | 1.0095 | 1091.75 |
| 2024 | p50_runner | 388 | -38.38 | -0.0989 | 0.9939 | 989.50 |
| 2024 | p50_be_runner | 389 | +2.00 | +0.0051 | 1.0003 | 965.25 |
| 2025 | TP100 control | 486 | +1103.25 | +2.2701 | 1.1220 | 758.50 |
| 2025 | p50_runner | 486 | +603.00 | +1.2407 | 1.0758 | 651.25 |
| 2025 | p50_be_runner | 486 | +637.00 | +1.3107 | 1.0801 | 608.50 |

## Combined descriptive totals

| Model | Trades | Net points | Net points / trade |
| --- | ---: | ---: | ---: |
| TP100 control | 1218 | +2172.50 | +1.7837 |
| p50_runner | 1218 | +1536.87 | +1.2618 |
| p50_be_runner | 1227 | +1637.25 | +1.3344 |

## Interpretation

The runner experiments reduced annual drawdown in all three years relative to the TP100 control.

The break-even runner improved net points over the plain runner in all three years:

- 2023: +998.25 vs +972.25
- 2024: +2.00 vs -38.38
- 2025: +637.00 vs +603.00

However, both runner variants sacrificed too much upside compared with keeping the full position open to TP100.

The 50% partial size is therefore too aggressive to justify a production change based on these research years.

## Decision

**KEEP TP100 AS THE CURRENT CONTROL — NO PRODUCTION CHANGE.**

R6.1 does not support taking 50% off at +50 as the default management rule.

The evidence does support continued partial-exit research because:

- drawdown improved consistently;
- the break-even overlay generally improved the 50/50 runner result;
- the main weakness appears to be giving up too much of the large runner, not the concept of partial realization itself.

## Next experiment

Proceed within the existing R6 exit-management family with a smaller partial at +50 while preserving more exposure to +100.

Recommended next isolated experiment:

- 25% at +50 / 75% runner to +100
- compare original-stop runner versus next-bar break-even runner
- retain TP100 control
- keep all entry, score, setup, stop, session and slippage behavior frozen

Do not combine score-model changes with this experiment.
