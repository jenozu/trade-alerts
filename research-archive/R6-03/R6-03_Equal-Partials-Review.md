# R6.3 — Equal Partials TP1/TP2/TP3/TP4 Review

## Status

Completed full chronological replays for 2023, 2024 and 2025.

The frozen TP100 control passed exact trade-ledger parity in all three years:

- 2023: 344 trades
- 2024: 388 trades
- 2025: 486 trades

R6.3 tested equal 25% partials at +25 / +50 / +75 / +100 with the original stop retained.
No break-even, trailing, scoring, entry, setup, timing, or production settings were changed.

## Year-by-year results

| Year | Model | Trades | Net points | Expectancy | PF | Max DD |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2023 | TP100 control | 344 | +1003.00 | +2.9157 | 1.1749 | 545.50 |
| 2023 | equal_partials | 344 | +831.75 | +2.4179 | 1.1784 | 372.19 |
| 2024 | TP100 control | 388 | +66.25 | +0.1707 | 1.0095 | 1091.75 |
| 2024 | equal_partials | 388 | -277.44 | -0.7150 | 0.9524 | 894.88 |
| 2025 | TP100 control | 486 | +1103.25 | +2.2701 | 1.1220 | 758.50 |
| 2025 | equal_partials | 486 | +99.44 | +0.2046 | 1.0138 | 666.12 |

## Combined descriptive totals

- TP100 control: 1,218 trades, +2,172.50 net points, +1.7837 points/trade.
- Equal partials: 1,218 trades, +653.75 net points, +0.5367 points/trade.

## Decision

**REJECT AS DEFAULT EXIT MODEL — NO PRODUCTION CHANGE.**

Equal partials reduced max drawdown in all three years but materially reduced expectancy and net profit.
2024 turned negative and 2025 lost most of the TP100 upside.

The strongest partial-exit candidate tested remains R6.2's 25% at +50 with a 75% TP100 break-even runner, but even that did not beat TP100 over the full 2023–2025 research universe.

Close the current fixed-target / partial-exit research block for now. Keep TP100 as the production control and move to independent Phase R5 stop-loss research rather than further partial-size tuning on the same sample.
