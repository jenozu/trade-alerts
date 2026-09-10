# EXP-001 — Score-band baseline analysis

## Method

This is a ledger-only diagnostic. It did not rerun the feature or backtest pipeline and did not change score weights, entries, stops, or targets.

## Inputs

- 2023: `/docker/trade-alerts-2023/data/results/backtest/trades.csv`
- 2024: `/docker/trade-alerts-2024/data/results/backtest/trades.csv`
- 2025: `/docker/trade-alerts/data/results/research_runs/2025_pipeline_final/backtest/trades.csv`

## Overall

| Band | Trades | Win rate | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Avg MAE | Avg hold min |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| All scored trades | 1218 | 27.8% | 1.78 | 0.071 | 1.10 | 2172.50 | 47.1% | 32.8% | 21.8% | 14.6% | 70.5% | 39.47 | 27.07 | 18.44 |

## Score buckets

| Band | Trades | Win rate | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Avg MAE | Avg hold min |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 70-79 | 958 | 27.7% | 0.82 | 0.033 | 1.05 | 788.00 | 47.3% | 32.3% | 21.2% | 13.2% | 70.4% | 39.23 | 26.90 | 19.05 |
| 80-89 | 239 | 27.2% | 4.59 | 0.182 | 1.25 | 1096.75 | 45.6% | 33.1% | 23.8% | 19.7% | 72.0% | 39.27 | 27.51 | 16.10 |
| 90-100 | 21 | 38.1% | 13.70 | 0.548 | 1.88 | 287.75 | 57.1% | 52.4% | 28.6% | 23.8% | 61.9% | 52.74 | 29.75 | 17.10 |

### 70-79 segmentation

| Segment | Trades | Win rate | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Avg MAE | Avg hold min |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2023 | 268 | 34.0% | 3.62 | 0.146 | 1.22 | 969.25 | 51.9% | 34.7% | 20.9% | 11.6% | 64.2% | 39.87 | 24.22 | 23.93 |
| 2024 | 305 | 27.9% | -0.24 | -0.009 | 0.99 | -73.25 | 45.2% | 30.8% | 20.7% | 11.5% | 69.5% | 37.26 | 25.86 | 21.39 |
| 2025 | 385 | 23.1% | -0.28 | -0.012 | 0.99 | -108.00 | 45.7% | 31.7% | 21.8% | 15.6% | 75.3% | 40.34 | 29.59 | 13.79 |
| long | 509 | 29.7% | 1.67 | 0.068 | 1.10 | 851.25 | 47.2% | 33.4% | 21.4% | 12.0% | 68.2% | 39.30 | 27.00 | 21.11 |
| short | 449 | 25.4% | -0.14 | -0.007 | 0.99 | -63.25 | 47.4% | 31.0% | 20.9% | 14.5% | 72.8% | 39.15 | 26.78 | 16.71 |

### 80-89 segmentation

| Segment | Trades | Win rate | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Avg MAE | Avg hold min |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2023 | 73 | 24.7% | -0.67 | -0.030 | 0.96 | -48.75 | 49.3% | 32.9% | 21.9% | 13.7% | 74.0% | 38.73 | 25.70 | 22.23 |
| 2024 | 78 | 26.9% | 3.41 | 0.137 | 1.18 | 265.75 | 41.0% | 30.8% | 23.1% | 17.9% | 73.1% | 35.96 | 24.89 | 16.42 |
| 2025 | 88 | 29.5% | 10.00 | 0.399 | 1.57 | 879.75 | 46.6% | 35.2% | 26.1% | 26.1% | 69.3% | 42.64 | 31.32 | 10.74 |
| long | 131 | 30.5% | 7.52 | 0.297 | 1.43 | 984.75 | 48.9% | 36.6% | 26.0% | 19.8% | 68.7% | 41.30 | 27.85 | 17.52 |
| short | 108 | 23.1% | 1.04 | 0.042 | 1.05 | 112.00 | 41.7% | 28.7% | 21.3% | 19.4% | 75.9% | 36.80 | 27.09 | 14.39 |

### 90-100 segmentation

| Segment | Trades | Win rate | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Avg MAE | Avg hold min |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2023 | 3 | 66.7% | 27.50 | 1.100 | 4.27 | 82.50 | 66.7% | 66.7% | 33.3% | 0.0% | 33.3% | 51.50 | 16.58 | 40.00 |
| 2024 | 5 | 0.0% | -25.25 | -1.010 | 0.00 | -126.25 | 40.0% | 40.0% | 0.0% | 0.0% | 100.0% | 33.05 | 32.20 | 15.60 |
| 2025 | 13 | 46.2% | 25.50 | 1.020 | 2.88 | 331.50 | 61.5% | 53.8% | 38.5% | 38.5% | 53.8% | 60.60 | 31.85 | 12.38 |
| long | 13 | 30.8% | 6.27 | 0.251 | 1.36 | 81.50 | 46.2% | 38.5% | 23.1% | 23.1% | 69.2% | 44.88 | 33.46 | 13.85 |
| short | 8 | 50.0% | 25.78 | 1.031 | 3.04 | 206.25 | 75.0% | 75.0% | 37.5% | 25.0% | 50.0% | 65.50 | 23.72 | 22.38 |

## Monotonicity and interpretation

- Eligible bands (at least 30 trades): 70-79, 80-89.
- Expectancy non-decreasing: **True**.
- Profit factor non-decreasing: **True**.
- Result: **insufficient eligible score bands**.
- Sample-size rule: Bands with fewer than 30 trades are exploratory, not proof.

## Decision

Diagnostic only — do not change score weights from this report. The raw 0–100 confluence score remains an ordinal ranking signal, not a win probability; probability calibration requires a separate validated model.
