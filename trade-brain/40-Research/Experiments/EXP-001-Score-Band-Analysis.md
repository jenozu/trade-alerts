# EXP-001 — Score-Band Baseline Analysis

Status: Complete

## Question

Does the current 0–100 confluence score meaningfully rank setup quality across the completed 2023, 2024, and 2025 baselines?

## Control

Untouched completed annual baselines for 2023, 2024, and 2025. No score weights were changed for this experiment.

## Inputs

- 2023 ledger: `/docker/trade-alerts-2023/data/results/backtest/trades.csv`
- 2024 ledger: `/docker/trade-alerts-2024/data/results/backtest/trades.csv`
- 2025 ledger: `/docker/trade-alerts/data/results/research_runs/2025_pipeline_final/backtest/trades.csv`

## Observed aggregate score buckets

| Score band | Trades | Win rate | Expectancy pts | Expectancy R | Profit factor | Net pts |
|---|---:|---:|---:|---:|---:|---:|
| 70–79 | 958 | 27.7% | +0.82 | +0.033 | 1.05 | +788.00 |
| 80–89 | 239 | 27.2% | +4.59 | +0.182 | 1.25 | +1096.75 |
| 90–100 | 21 | 38.1% | +13.70 | +0.548 | 1.88 | +287.75 |

No 50–59 or 60–69 trades appeared in the completed trade ledgers, so those bands cannot be evaluated from executed-trade results alone.

## Direction observations

### 70–79

- Long: 509 trades, +1.67 pts expectancy, PF 1.10.
- Short: 449 trades, -0.14 pts expectancy, PF 0.99.

### 80–89

- Long: 131 trades, +7.52 pts expectancy, PF 1.43.
- Short: 108 trades, +1.04 pts expectancy, PF 1.05.

## Interpretation

- Win rate is not strictly monotonic because 80–89 has a slightly lower win rate than 70–79.
- Expectancy and profit factor improve materially across the observed bands.
- 80–89 appears materially stronger than 70–79.
- 90–100 is promising but has only 21 trades and is therefore preliminary.
- The current score appears substantially better calibrated for long setups than short setups.
- Year-to-year behavior is mixed, so regime dependence remains an important limitation.
- The score should remain an ordinal confluence-quality score, not be represented as a probability.

## Resulting findings

- [[../Findings/F001-Score-Expectancy-Ordering]]
- [[../Findings/F002-80-89-Outperforms-70-79]]
- [[../Findings/F003-90-100-Sample-Too-Small]]
- [[../Findings/F004-Long-Short-Score-Asymmetry]]
- [[../Findings/F005-Year-Regime-Dependence]]
- [[../Findings/F006-Score-Is-Ordinal-Not-Probability]]

## Next

EXP-002 — Long vs. Short. Investigate the direction asymmetry exposed here before changing score weights.
