# EXP-007 — Liquidity Sweep Contribution

Diagnostic only. Existing baseline ledgers and scored feature artifacts only.

## Coverage

- Exact feature match: **1218/1218 (100.0%)**

## Sweep present vs absent

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 185 | 30.8% | 5.93 | 0.234 | 1.34 | 1096.25 | 53.0% | 34.6% | 25.4% | 20.5% | 68.1% |
| True | 1033 | 27.2% | 1.04 | 0.042 | 1.06 | 1076.25 | 46.1% | 32.4% | 21.2% | 13.6% | 71.0% |

## By year

### 2023

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 46 | 32.6% | 3.76 | 0.146 | 1.22 | 173.00 | 47.8% | 30.4% | 19.6% | 15.2% | 67.4% |
| True | 298 | 32.2% | 2.79 | 0.113 | 1.17 | 830.00 | 52.0% | 35.2% | 21.5% | 11.4% | 65.8% |

### 2024

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 60 | 36.7% | 9.88 | 0.391 | 1.63 | 592.75 | 50.0% | 35.0% | 30.0% | 23.3% | 61.7% |
| True | 328 | 25.6% | -1.61 | -0.063 | 0.91 | -526.50 | 43.3% | 30.2% | 19.2% | 10.7% | 72.3% |

### 2025

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 79 | 25.3% | 4.18 | 0.167 | 1.22 | 330.50 | 58.2% | 36.7% | 25.3% | 21.5% | 73.4% |
| True | 407 | 24.8% | 1.90 | 0.075 | 1.10 | 772.75 | 44.0% | 32.2% | 22.6% | 17.4% | 73.7% |

## By direction

### long

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 75 | 29.3% | 1.51 | 0.056 | 1.09 | 113.00 | 50.7% | 29.3% | 21.3% | 16.0% | 69.3% |
| True | 578 | 29.9% | 3.12 | 0.126 | 1.18 | 1804.50 | 47.1% | 34.8% | 22.5% | 13.5% | 68.2% |

### short

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 110 | 31.8% | 8.94 | 0.356 | 1.52 | 983.25 | 54.5% | 38.2% | 28.2% | 23.6% | 67.3% |
| True | 455 | 23.7% | -1.60 | -0.064 | 0.91 | -728.25 | 44.8% | 29.5% | 19.6% | 13.6% | 74.5% |

## By setup family

### reversal

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| True | 1033 | 27.2% | 1.04 | 0.042 | 1.06 | 1076.25 | 46.1% | 32.4% | 21.2% | 13.6% | 71.0% |

### continuation

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 185 | 30.8% | 5.93 | 0.234 | 1.34 | 1096.25 | 53.0% | 34.6% | 25.4% | 20.5% | 68.1% |

## Sweep side

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| buy_side | 455 | 23.7% | -1.60 | -0.064 | 0.91 | -728.25 | 44.8% | 29.5% | 19.6% | 13.6% | 74.5% |
| sell_side | 578 | 29.9% | 3.12 | 0.126 | 1.18 | 1804.50 | 47.1% | 34.8% | 22.5% | 13.5% | 68.2% |

## Sweep source

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| active_external_swing_high | 128 | 25.8% | 2.05 | 0.078 | 1.12 | 263.00 | 51.6% | 30.5% | 20.3% | 15.6% | 70.3% |
| active_external_swing_low | 186 | 29.6% | 2.53 | 0.107 | 1.15 | 471.25 | 45.2% | 33.3% | 22.6% | 12.9% | 68.3% |
| active_internal_swing_high | 257 | 23.7% | -2.73 | -0.109 | 0.86 | -700.50 | 43.2% | 29.2% | 18.7% | 12.5% | 75.5% |
| active_internal_swing_low | 254 | 31.5% | 6.06 | 0.242 | 1.36 | 1539.50 | 49.6% | 37.8% | 24.0% | 15.7% | 66.1% |
| ash | 1 | 0.0% | -25.25 | -1.010 | 0.00 | -25.25 | 0.0% | 0.0% | 0.0% | 0.0% | 100.0% |
| asl | 11 | 45.5% | 11.11 | 0.430 | 1.83 | 122.25 | 63.6% | 36.4% | 18.2% | 18.2% | 54.5% |
| loh | 13 | 23.1% | 5.04 | 0.198 | 1.28 | 65.50 | 61.5% | 46.2% | 30.8% | 23.1% | 69.2% |
| lol | 19 | 15.8% | -13.38 | -0.545 | 0.36 | -254.25 | 42.1% | 36.8% | 10.5% | 0.0% | 84.2% |
| onh | 13 | 15.4% | -6.02 | -0.241 | 0.72 | -78.25 | 23.1% | 23.1% | 15.4% | 15.4% | 84.6% |
| onl | 31 | 32.3% | 6.27 | 0.250 | 1.38 | 194.25 | 58.1% | 35.5% | 29.0% | 19.4% | 64.5% |
| pdh | 5 | 20.0% | -10.20 | -0.408 | 0.50 | -51.00 | 60.0% | 20.0% | 20.0% | 0.0% | 80.0% |
| pdl | 8 | 12.5% | -9.62 | -0.385 | 0.56 | -77.00 | 25.0% | 25.0% | 12.5% | 12.5% | 87.5% |
| pmh | 38 | 21.1% | -5.31 | -0.202 | 0.73 | -201.75 | 34.2% | 26.3% | 21.1% | 13.2% | 78.9% |
| pml | 69 | 27.5% | -2.78 | -0.111 | 0.85 | -191.50 | 39.1% | 27.5% | 18.8% | 7.2% | 72.5% |

## Confirmation after sweep

### sweep_then_displacement

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 264 | 23.9% | -4.30 | -0.171 | 0.77 | -1134.25 | 39.4% | 27.7% | 18.9% | 9.1% | 73.9% |
| True | 769 | 28.3% | 2.87 | 0.115 | 1.16 | 2210.50 | 48.4% | 34.1% | 22.0% | 15.1% | 70.0% |

### sweep_then_mss

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 569 | 25.8% | -0.78 | -0.032 | 0.96 | -441.75 | 45.5% | 30.8% | 19.3% | 11.8% | 71.7% |
| True | 464 | 28.9% | 3.27 | 0.132 | 1.19 | 1518.00 | 46.8% | 34.5% | 23.5% | 15.7% | 70.0% |

### sweep_then_choch

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 569 | 25.8% | -0.78 | -0.032 | 0.96 | -441.75 | 45.5% | 30.8% | 19.3% | 11.8% | 71.7% |
| True | 464 | 28.9% | 3.27 | 0.132 | 1.19 | 1518.00 | 46.8% | 34.5% | 23.5% | 15.7% | 70.0% |

### sweep_then_bos

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 781 | 27.3% | 0.93 | 0.038 | 1.05 | 727.00 | 46.5% | 32.5% | 21.4% | 13.6% | 70.8% |
| True | 252 | 27.0% | 1.39 | 0.053 | 1.08 | 349.25 | 44.8% | 32.1% | 20.6% | 13.5% | 71.4% |

### sweep_then_fvg

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 588 | 27.4% | 1.52 | 0.061 | 1.09 | 893.25 | 47.8% | 33.3% | 21.3% | 14.1% | 70.4% |
| True | 445 | 27.0% | 0.41 | 0.017 | 1.02 | 183.00 | 43.8% | 31.2% | 21.1% | 12.8% | 71.7% |

## Sweep penetration quartiles

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| (0.249, 2.25] | 278 | 28.1% | 1.62 | 0.063 | 1.09 | 449.75 | 45.3% | 30.6% | 20.9% | 12.9% | 69.8% |
| (2.25, 5.0] | 246 | 28.5% | 0.80 | 0.033 | 1.05 | 196.00 | 48.8% | 34.6% | 22.8% | 12.2% | 69.9% |
| (5.0, 9.5] | 261 | 30.7% | 4.61 | 0.188 | 1.27 | 1204.50 | 49.0% | 33.7% | 23.8% | 16.5% | 67.0% |
| (9.5, 274.5] | 248 | 21.4% | -3.12 | -0.127 | 0.84 | -774.00 | 41.1% | 31.0% | 17.3% | 12.5% | 77.4% |

## Sweep recency

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1-2_bars | 257 | 23.0% | -2.22 | -0.088 | 0.88 | -569.50 | 46.3% | 30.4% | 20.2% | 12.1% | 75.1% |
| 3-5_bars | 257 | 31.1% | 2.53 | 0.104 | 1.15 | 649.25 | 47.5% | 33.9% | 21.8% | 14.4% | 68.1% |
| 6-9_bars | 260 | 27.3% | 1.66 | 0.065 | 1.09 | 432.75 | 42.3% | 30.4% | 21.2% | 13.1% | 70.4% |
| same_bar | 259 | 27.4% | 2.18 | 0.087 | 1.12 | 563.75 | 48.3% | 35.1% | 21.6% | 14.7% | 70.3% |

## Score-band interaction

### 70-79

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 160 | 30.0% | 4.36 | 0.171 | 1.25 | 697.25 | 52.5% | 34.4% | 24.4% | 19.4% | 68.8% |
| True | 798 | 27.2% | 0.11 | 0.005 | 1.01 | 90.75 | 46.2% | 31.8% | 20.6% | 11.9% | 70.7% |

### 80-89

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 25 | 36.0% | 15.96 | 0.638 | 1.99 | 399.00 | 56.0% | 36.0% | 32.0% | 28.0% | 64.0% |
| True | 214 | 26.2% | 3.26 | 0.129 | 1.18 | 697.75 | 44.4% | 32.7% | 22.9% | 18.7% | 72.9% |

### 90-100

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| True | 21 | 38.1% | 13.70 | 0.548 | 1.88 | 287.75 | 57.1% | 52.4% | 28.6% | 23.8% | 61.9% |

## Capability / definition notes

- Production liquidity sweep requires penetration and a **close back through the level on the sweep bar**.
- Therefore a separate `wick-only reclaim sweep` category is not available and is not invented.
- `bars_since_sweep` measures how recently the qualifying sweep occurred before the trade signal; it is not a separate reclaim-speed measurement.

## Inputs

- 2023 ledger: `/docker/trade-alerts-2023/data/results/backtest/trades.csv`
- 2023 features: `/docker/trade-alerts-2023/data/processed/scoring/nq_1m_scored.parquet`
- 2024 ledger: `/docker/trade-alerts-2024/data/results/backtest/trades.csv`
- 2024 features: `/docker/trade-alerts-2024/data/processed/scoring/nq_1m_scored.parquet`
- 2025 ledger: `/docker/trade-alerts/data/results/research_runs/2025_pipeline_final/backtest/trades.csv`
- 2025 features: `/docker/trade-alerts/data/cache/2025_warmup_92d/features_scored.parquet`

## Research discipline

- EXP-007 is diagnostic only.
- No score weights, entries, stops, targets, or setup logic changed.
- Small cells should be treated as exploratory.