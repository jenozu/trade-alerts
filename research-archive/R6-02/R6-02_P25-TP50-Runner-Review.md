# R6.2 — 25% TP50 + 75% TP100 Runner Review

## Status

Completed full chronological replays for 2023, 2024 and 2025.

The frozen TP100 control passed exact trade-ledger parity in all three years:

- 2023: 344 trades
- 2024: 388 trades
- 2025: 486 trades

Models reviewed:

1. `p25_runner` — 25% exits at +50 points; 75% remains for +100; original stop remains.
2. `p25_be_runner` — 25% exits at +50 points; 75% remains for +100; runner moves to break-even beginning on the next bar.

No production settings were changed.

## Year-by-year results

| Year | Model | Trades | Net points | Expectancy | PF | Max DD |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2023 | TP100 control | 344 | +1003.00 | +2.9157 | 1.1749 | 545.50 |
| 2023 | p25_runner | 344 | +987.62 | +2.8710 | 1.1852 | 479.88 |
| 2023 | p25_be_runner | 352 | +1015.12 | +2.8839 | 1.1905 | 510.94 |
| 2024 | TP100 control | 388 | +66.25 | +0.1707 | 1.0095 | 1091.75 |
| 2024 | p25_runner | 388 | +13.94 | +0.0359 | 1.0022 | 1040.62 |
| 2024 | p25_be_runner | 389 | +87.12 | +0.2240 | 1.0137 | 991.62 |
| 2025 | TP100 control | 486 | +1103.25 | +2.2701 | 1.1220 | 758.50 |
| 2025 | p25_runner | 486 | +853.12 | +1.7554 | 1.1036 | 704.88 |
| 2025 | p25_be_runner | 486 | +904.12 | +1.8603 | 1.1137 | 633.50 |

## Combined descriptive totals

| Model | Trades | Net points | Net points / trade |
| --- | ---: | ---: | ---: |
| TP100 control | 1218 | +2172.50 | +1.7837 |
| p25_runner | 1218 | +1854.68 | +1.5227 |
| p25_be_runner | 1227 | +2006.36 | +1.6352 |

## Interpretation

Reducing the partial size from 50% to 25% materially improved the runner results.

The break-even version outperformed the plain 25% runner in all three years:

- 2023: +1015.12 vs +987.62
- 2024: +87.12 vs +13.94
- 2025: +904.12 vs +853.12

The 25% + break-even runner also improved the control in 2023 and 2024, while reducing maximum drawdown in every year.

However, it still sacrificed too much of the strong 2025 TP100 upside. Across all three research years, TP100 remained ahead by 166.14 net points and retained higher pooled expectancy.

## Decision

**INVESTIGATE — NO PRODUCTION CHANGE.**

R6.2 is the strongest partial-exit candidate tested so far, especially from a drawdown perspective, but it does not yet beat the TP100 control across the full research universe.

Do not continue shrinking the TP50 partial fraction repeatedly on the same 2023–2025 sample. That would turn a controlled experiment into parameter mining.

## Next nonredundant exit experiment

Proceed to a structurally different exit model already defined in the roadmap rather than another nearby TP50 partial-size tweak.

Recommended next test:

- equal 25% partials at TP1 / TP2 / TP3 / TP4;
- frozen entries, scoring, stop logic, timing and slippage;
- TP100 control parity gate;
- full chronological replay by year.

This directly tests whether distributing realization across the existing milestone ladder improves MFE capture and drawdown without overfitting a single partial percentage.
