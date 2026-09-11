# EXP-006 — HTF Bias

Diagnostic only; exact signal-time join to existing scored feature artifacts. No historical pipeline rerun and no strategy/scoring changes.

## Inputs

- 2023 ledger: `/docker/trade-alerts-2023/data/results/backtest/trades.csv`
- 2023 features: `/docker/trade-alerts-2023/data/processed/scoring/nq_1m_scored.parquet`
- 2024 ledger: `/docker/trade-alerts-2024/data/results/backtest/trades.csv`
- 2024 features: `/docker/trade-alerts-2024/data/processed/scoring/nq_1m_scored.parquet`
- 2025 ledger: `/docker/trade-alerts/data/results/research_runs/2025_pipeline_final/backtest/trades.csv`
- 2025 features: `/docker/trade-alerts/data/cache/2025_warmup_92d/features_scored.parquet`

## Feature-join coverage

- Matched: **1218/1218 (100.0%)**

## Production intraday HTF context

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Med MFE | Avg MAE | Med MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aligned | 803 | 27.9% | 1.86 | 0.074 | 1.10 | 1491.75 | 48.4% | 32.9% | 21.2% | 14.9% | 70.5% | 39.80 | 24.00 | 27.02 | 27.50 |
| conflicting | 415 | 27.5% | 1.64 | 0.066 | 1.09 | 680.75 | 44.6% | 32.5% | 23.1% | 14.0% | 70.6% | 38.84 | 19.75 | 27.17 | 27.25 |
| neutral | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| unknown | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

Headline `conflicting` includes a directional intraday bias opposed to the trade or an explicit conflict among the intraday HTF components.

## Pure intraday directional relation

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Med MFE | Avg MAE | Med MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aligned | 1119 | 28.2% | 2.16 | 0.087 | 1.12 | 2415.50 | 47.1% | 33.2% | 21.9% | 14.7% | 70.2% | 39.40 | 22.50 | 26.99 | 27.50 |
| opposed | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| neutral | 99 | 22.2% | -2.45 | -0.103 | 0.87 | -243.00 | 47.5% | 28.3% | 21.2% | 13.1% | 74.7% | 40.26 | 29.00 | 27.93 | 27.00 |
| unknown | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

## By year

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Med MFE | Avg MAE | Med MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2023 aligned | 203 | 33.0% | 2.23 | 0.090 | 1.13 | 453.00 | 52.7% | 35.5% | 19.2% | 11.3% | 66.0% | 39.47 | 29.00 | 24.21 | 26.50 |
| 2023 conflicting | 141 | 31.2% | 3.90 | 0.156 | 1.23 | 550.00 | 49.6% | 33.3% | 24.1% | 12.8% | 66.0% | 40.10 | 23.50 | 24.84 | 26.75 |
| 2023 neutral | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| 2023 unknown | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| 2024 aligned | 265 | 26.0% | -0.81 | -0.031 | 0.96 | -215.25 | 44.2% | 29.8% | 20.0% | 12.8% | 71.7% | 36.51 | 21.00 | 26.00 | 27.00 |
| 2024 conflicting | 123 | 30.1% | 2.29 | 0.091 | 1.13 | 281.50 | 44.7% | 33.3% | 22.8% | 12.2% | 68.3% | 37.89 | 19.25 | 25.21 | 26.75 |
| 2024 neutral | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| 2024 unknown | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| 2025 aligned | 335 | 26.3% | 3.74 | 0.148 | 1.21 | 1254.00 | 49.3% | 33.7% | 23.3% | 18.8% | 72.2% | 42.60 | 26.75 | 29.52 | 28.50 |
| 2025 conflicting | 151 | 21.9% | -1.00 | -0.039 | 0.95 | -150.75 | 39.7% | 31.1% | 22.5% | 16.6% | 76.8% | 38.42 | 19.00 | 30.94 | 30.00 |
| 2025 neutral | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| 2025 unknown | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

## By setup family

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Med MFE | Avg MAE | Med MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| continuation aligned | 142 | 30.3% | 5.35 | 0.211 | 1.31 | 760.25 | 51.4% | 33.1% | 24.6% | 20.4% | 69.0% | 42.89 | 28.50 | 26.39 | 27.00 |
| continuation conflicting | 43 | 32.6% | 7.81 | 0.311 | 1.47 | 336.00 | 58.1% | 39.5% | 27.9% | 20.9% | 65.1% | 46.37 | 29.75 | 25.44 | 27.00 |
| continuation neutral | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| continuation unknown | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| reversal aligned | 661 | 27.4% | 1.11 | 0.045 | 1.06 | 731.50 | 47.8% | 32.8% | 20.4% | 13.8% | 70.8% | 39.13 | 23.50 | 27.15 | 27.50 |
| reversal conflicting | 372 | 26.9% | 0.93 | 0.037 | 1.05 | 344.75 | 43.0% | 31.7% | 22.6% | 13.2% | 71.2% | 37.96 | 19.50 | 27.37 | 27.25 |
| reversal neutral | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| reversal unknown | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

## By direction

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Med MFE | Avg MAE | Med MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| long aligned | 424 | 30.4% | 3.25 | 0.130 | 1.19 | 1378.00 | 49.1% | 34.4% | 21.5% | 14.4% | 67.7% | 40.53 | 25.50 | 27.21 | 27.12 |
| long conflicting | 229 | 28.8% | 2.36 | 0.096 | 1.13 | 539.50 | 44.5% | 33.6% | 24.0% | 12.7% | 69.4% | 38.48 | 19.75 | 27.47 | 27.50 |
| long neutral | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| long unknown | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| short aligned | 379 | 25.1% | 0.30 | 0.012 | 1.02 | 113.75 | 47.8% | 31.1% | 20.8% | 15.6% | 73.6% | 38.97 | 22.50 | 26.80 | 27.75 |
| short conflicting | 186 | 25.8% | 0.76 | 0.029 | 1.04 | 141.25 | 44.6% | 31.2% | 22.0% | 15.6% | 72.0% | 39.27 | 19.75 | 26.80 | 27.00 |
| short neutral | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| short unknown | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

## Individual timeframe contribution

### 1d

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Med MFE | Avg MAE | Med MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aligned | 565 | 29.9% | 2.30 | 0.090 | 1.13 | 1298.25 | 47.1% | 33.6% | 22.1% | 13.5% | 68.3% | 39.31 | 22.75 | 26.71 | 27.00 |
| opposed | 580 | 25.7% | 1.04 | 0.042 | 1.06 | 603.00 | 46.0% | 31.2% | 21.0% | 15.3% | 72.4% | 39.14 | 21.62 | 27.49 | 27.50 |
| neutral | 65 | 26.2% | 2.21 | 0.094 | 1.12 | 143.50 | 56.9% | 38.5% | 24.6% | 16.9% | 73.8% | 43.67 | 32.00 | 26.45 | 27.50 |
| unknown | 8 | 37.5% | 15.97 | 0.639 | 2.01 | 127.75 | 50.0% | 37.5% | 37.5% | 25.0% | 62.5% | 40.69 | 18.00 | 27.28 | 31.50 |
- Aligned-minus-known-non-aligned expectancy lift: **1.14 pts/trade**.

### 4h

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Med MFE | Avg MAE | Med MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aligned | 641 | 29.0% | 2.70 | 0.109 | 1.15 | 1733.75 | 46.3% | 34.9% | 21.8% | 14.8% | 69.6% | 39.43 | 21.50 | 26.47 | 27.25 |
| opposed | 563 | 25.9% | 0.32 | 0.012 | 1.02 | 182.50 | 47.8% | 30.2% | 21.5% | 14.0% | 71.9% | 39.36 | 23.75 | 27.74 | 27.50 |
| neutral | 14 | 42.9% | 18.30 | 0.732 | 2.27 | 256.25 | 57.1% | 35.7% | 35.7% | 28.6% | 57.1% | 45.73 | 30.88 | 27.68 | 31.50 |
| unknown | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
- Aligned-minus-known-non-aligned expectancy lift: **1.94 pts/trade**.

### 1h

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Med MFE | Avg MAE | Med MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aligned | 1169 | 28.1% | 1.99 | 0.080 | 1.11 | 2328.50 | 47.0% | 33.1% | 22.1% | 14.6% | 70.1% | 39.47 | 22.25 | 26.96 | 27.25 |
| opposed | 49 | 18.4% | -3.18 | -0.138 | 0.84 | -156.00 | 51.0% | 24.5% | 16.3% | 14.3% | 79.6% | 39.51 | 31.75 | 29.73 | 27.50 |
| neutral | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| unknown | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
- Aligned-minus-known-non-aligned expectancy lift: **5.18 pts/trade**.

### 30m

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Med MFE | Avg MAE | Med MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aligned | 1103 | 27.3% | 1.26 | 0.050 | 1.07 | 1388.00 | 46.9% | 32.1% | 20.8% | 14.4% | 71.1% | 38.83 | 22.25 | 27.30 | 27.50 |
| opposed | 115 | 32.2% | 6.82 | 0.273 | 1.42 | 784.50 | 49.6% | 39.1% | 32.2% | 16.5% | 65.2% | 45.61 | 28.25 | 24.86 | 26.75 |
| neutral | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| unknown | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
- Aligned-minus-known-non-aligned expectancy lift: **-5.56 pts/trade**.

### 15m

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Med MFE | Avg MAE | Med MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aligned | 917 | 28.0% | 2.41 | 0.095 | 1.14 | 2207.25 | 49.0% | 33.3% | 22.0% | 15.3% | 70.3% | 40.44 | 24.75 | 26.94 | 27.50 |
| opposed | 301 | 26.9% | -0.12 | -0.003 | 0.99 | -34.75 | 41.5% | 31.2% | 21.3% | 12.6% | 71.1% | 36.50 | 18.75 | 27.47 | 27.00 |
| neutral | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| unknown | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
- Aligned-minus-known-non-aligned expectancy lift: **2.52 pts/trade**.

## Pairwise timeframe redundancy diagnostics

- 1d vs 4h: known directional pairs=1145, state agreement=63.9%; both aligned n=380, exp=1.37, PF=1.08.
- 1d vs 1h: known directional pairs=1145, state agreement=49.6%; both aligned n=544, exp=2.27, PF=1.13.
- 1d vs 30m: known directional pairs=1145, state agreement=50.9%; both aligned n=520, exp=1.58, PF=1.09.
- 1d vs 15m: known directional pairs=1145, state agreement=51.7%; both aligned n=434, exp=2.24, PF=1.13.
- 4h vs 1h: known directional pairs=1204, state agreement=55.0%; both aligned n=627, exp=2.99, PF=1.17.
- 4h vs 30m: known directional pairs=1204, state agreement=50.7%; both aligned n=568, exp=1.69, PF=1.10.
- 4h vs 15m: known directional pairs=1204, state agreement=52.8%; both aligned n=489, exp=3.60, PF=1.20.
- 1h vs 30m: known directional pairs=1218, state agreement=86.5%; both aligned n=1054, exp=1.46, PF=1.08.
- 1h vs 15m: known directional pairs=1218, state agreement=71.3%; both aligned n=868, exp=2.72, PF=1.15.
- 30m vs 15m: known directional pairs=1218, state agreement=74.1%; both aligned n=852, exp=1.57, PF=1.09.

## Score-band × HTF context

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Med MFE | Avg MAE | Med MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 70-79 aligned | 624 | 29.5% | 2.59 | 0.104 | 1.15 | 1617.50 | 50.8% | 33.8% | 22.0% | 14.6% | 68.6% | 41.12 | 27.38 | 26.33 | 27.50 |
| 70-79 conflicting | 334 | 24.3% | -2.48 | -0.100 | 0.87 | -829.50 | 40.7% | 29.3% | 19.8% | 10.5% | 73.7% | 35.69 | 18.50 | 27.97 | 27.50 |
| 70-79 neutral | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| 70-79 unknown | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| 80-89 aligned | 167 | 22.2% | -0.64 | -0.029 | 0.97 | -107.50 | 39.5% | 28.7% | 18.6% | 16.2% | 77.2% | 34.58 | 14.75 | 29.25 | 27.25 |
| 80-89 conflicting | 72 | 38.9% | 16.73 | 0.672 | 2.11 | 1204.25 | 59.7% | 43.1% | 36.1% | 27.8% | 59.7% | 50.14 | 36.75 | 23.46 | 26.25 |
| 80-89 neutral | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| 80-89 unknown | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| 90-100 aligned | 12 | 25.0% | -1.52 | -0.061 | 0.92 | -18.25 | 50.0% | 41.7% | 16.7% | 16.7% | 75.0% | 43.38 | 31.88 | 31.58 | 28.50 |
| 90-100 conflicting | 9 | 55.6% | 34.00 | 1.360 | 4.03 | 306.00 | 66.7% | 66.7% | 44.4% | 33.3% | 44.4% | 65.22 | 65.75 | 27.31 | 14.00 |
| 90-100 neutral | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| 90-100 unknown | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

## SNR / RVOL by HTF context

- snr_1m: aligned: mean=1.90, median=1.79, n=803; conflicting: mean=1.96, median=1.82, n=415; neutral: mean=—, median=—, n=0; unknown: mean=—, median=—, n=0
- snr_5m: aligned: mean=1.63, median=1.42, n=803; conflicting: mean=1.85, median=1.60, n=415; neutral: mean=—, median=—, n=0; unknown: mean=—, median=—, n=0
- snr_15m: aligned: mean=2.18, median=1.91, n=803; conflicting: mean=1.76, median=1.45, n=415; neutral: mean=—, median=—, n=0; unknown: mean=—, median=—, n=0
- rvol_rolling: aligned: mean=2.70, median=1.78, n=803; conflicting: mean=2.60, median=1.61, n=415; neutral: mean=—, median=—, n=0; unknown: mean=—, median=—, n=0
- rvol_time_of_day: aligned: mean=1.40, median=1.31, n=785; conflicting: mean=1.39, median=1.31, n=411; neutral: mean=—, median=—, n=0; unknown: mean=—, median=—, n=0

## Liquidity/sweep interaction

### liquidity_sweep=False

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Med MFE | Avg MAE | Med MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aligned | 142 | 30.3% | 5.35 | 0.211 | 1.31 | 760.25 | 51.4% | 33.1% | 24.6% | 20.4% | 69.0% | 42.89 | 28.50 | 26.39 | 27.00 |
| conflicting | 43 | 32.6% | 7.81 | 0.311 | 1.47 | 336.00 | 58.1% | 39.5% | 27.9% | 20.9% | 65.1% | 46.37 | 29.75 | 25.44 | 27.00 |
| neutral | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| unknown | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

### liquidity_sweep=True

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Med MFE | Avg MAE | Med MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aligned | 661 | 27.4% | 1.11 | 0.045 | 1.06 | 731.50 | 47.8% | 32.8% | 20.4% | 13.8% | 70.8% | 39.13 | 23.50 | 27.15 | 27.50 |
| conflicting | 372 | 26.9% | 0.93 | 0.037 | 1.05 | 344.75 | 43.0% | 31.7% | 22.6% | 13.2% | 71.2% | 37.96 | 19.50 | 27.37 | 27.25 |
| neutral | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| unknown | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

## Current scoring contract

- Intraday production bias: 1h/30m/15m weighted {'1h': 3.0, '30m': 2.0, '15m': 1.0}.
- Macro context: 4h/1d weighted {'4h': 2.0, '1d': 1.0}; Daily remains `context_only`.
- Current score treatment: +10 points when aligned and -20 points when opposed.

## Time-of-day capability

- Available: **True**; reliable: **False**; distribution={'10:30+': 1218}.

## Limitations

- Diagnostic association does not prove unique causal contribution; pairwise agreement is a redundancy diagnostic, not an ablation result.
- Time-of-day conclusions are allowed only when the recorded timestamp buckets are demonstrably non-degenerate.
- Cells under 30 trades are exploratory.
