# EXP-002 — Long vs Short

Ledger-only diagnostic; no pipeline rerun and no strategy/scoring changes.

## Inputs

- 2023: `/docker/trade-alerts-2023/data/results/backtest/trades.csv`
- 2024: `/docker/trade-alerts-2024/data/results/backtest/trades.csv`
- 2025: `/docker/trade-alerts/data/results/research_runs/2025_pipeline_final/backtest/trades.csv`

## Overall direction comparison

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Med MFE | Avg MAE | Med MAE | Avg hold |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| LONG | 653 | 29.9% | 2.94 | 0.118 | 1.17 | 1917.50 | 47.5% | 34.2% | 22.4% | 13.8% | 68.3% | 39.81 | 23.75 | 27.30 | 27.25 | 20.25 |
| SHORT | 565 | 25.3% | 0.45 | 0.017 | 1.02 | 255.00 | 46.7% | 31.2% | 21.2% | 15.6% | 73.1% | 39.07 | 21.25 | 26.80 | 27.50 | 16.35 |

Long-minus-short expectancy gap: **2.49 points/trade**.

## Year-by-year

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Med MFE | Avg MAE | Med MAE | Avg hold |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2023 LONG | 181 | 32.0% | 2.33 | 0.093 | 1.14 | 422.00 | 50.8% | 34.3% | 21.5% | 10.5% | 66.3% | 38.91 | 26.00 | 24.69 | 26.50 | 23.56 |
| 2023 SHORT | 163 | 32.5% | 3.56 | 0.144 | 1.21 | 581.00 | 52.1% | 35.0% | 20.9% | 13.5% | 65.6% | 40.63 | 29.00 | 24.22 | 26.75 | 23.88 |
| 2024 LONG | 221 | 29.9% | 1.50 | 0.061 | 1.09 | 332.50 | 47.1% | 33.9% | 21.3% | 11.3% | 68.3% | 37.58 | 22.75 | 25.89 | 27.00 | 22.59 |
| 2024 SHORT | 167 | 24.0% | -1.59 | -0.063 | 0.91 | -266.25 | 40.7% | 26.9% | 20.4% | 14.4% | 73.7% | 36.10 | 17.75 | 25.56 | 27.00 | 17.31 |
| 2025 LONG | 251 | 28.3% | 4.63 | 0.186 | 1.26 | 1163.00 | 45.4% | 34.3% | 23.9% | 18.3% | 69.7% | 42.43 | 23.75 | 30.43 | 28.75 | 15.78 |
| 2025 SHORT | 235 | 21.3% | -0.25 | -0.013 | 0.99 | -59.75 | 47.2% | 31.5% | 22.1% | 17.9% | 77.9% | 40.09 | 22.00 | 29.46 | 29.00 | 10.43 |

## Score-band performance

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Med MFE | Avg MAE | Med MAE | Avg hold |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 70-79 LONG | 509 | 29.7% | 1.67 | 0.068 | 1.10 | 851.25 | 47.2% | 33.4% | 21.4% | 12.0% | 68.2% | 39.30 | 23.75 | 27.00 | 27.50 | 21.11 |
| 70-79 SHORT | 449 | 25.4% | -0.14 | -0.007 | 0.99 | -63.25 | 47.4% | 31.0% | 20.9% | 14.5% | 72.8% | 39.15 | 22.00 | 26.78 | 27.50 | 16.71 |
| 80-89 LONG | 131 | 30.5% | 7.52 | 0.297 | 1.43 | 984.75 | 48.9% | 36.6% | 26.0% | 19.8% | 68.7% | 41.30 | 22.75 | 27.85 | 26.50 | 17.52 |
| 80-89 SHORT | 108 | 23.1% | 1.04 | 0.042 | 1.05 | 112.00 | 41.7% | 28.7% | 21.3% | 19.4% | 75.9% | 36.80 | 17.50 | 27.09 | 27.25 | 14.39 |
| 90-100 LONG | 13 | 30.8% | 6.27 | 0.251 | 1.36 | 81.50 | 46.2% | 38.5% | 23.1% | 23.1% | 69.2% | 44.88 | 41.50 | 33.46 | 26.75 | 13.85 |
| 90-100 SHORT | 8 | 50.0% | 25.78 | 1.031 | 3.04 | 206.25 | 75.0% | 75.0% | 37.5% | 25.0% | 50.0% | 65.50 | 72.50 | 23.72 | 21.25 | 22.38 |

## Score distribution

- LONG: n=653, mean=76.11, median=74.42, std=5.45, bands={'70-79': 509, '80-89': 131, '90-100': 13}.
- SHORT: n=565, mean=75.36, median=73.59, std=5.11, bands={'70-79': 449, '80-89': 108, '90-100': 8}.

## Context diagnostics

### htf_bias

- `bearish` — long n=0, exp=—, PF=—; short n=511, exp=0.73, PF=1.04.
- `bullish` — long n=608, exp=3.36, PF=1.20; short n=0, exp=—, PF=—.
- `neutral` — long n=45, exp=-2.73, PF=0.85; short n=54, exp=-2.22, PF=0.88.

### dol_direction

- `bearish` — long n=1, exp=-25.25, PF=0.00; short n=558, exp=0.32, PF=1.02.
- `bullish` — long n=631, exp=3.16, PF=1.18; short n=0, exp=—, PF=—.
- `neutral` — long n=21, exp=-2.38, PF=0.88; short n=7, exp=10.57, PF=1.59.

### liquidity_sweep

- `False` — long n=75, exp=1.51, PF=1.09; short n=110, exp=8.94, PF=1.52.
- `True` — long n=578, exp=3.12, PF=1.18; short n=455, exp=-1.60, PF=0.91.

### displacement

- `False` — long n=187, exp=-3.49, PF=0.81; short n=141, exp=-1.04, PF=0.94.
- `True` — long n=466, exp=5.52, PF=1.33; short n=424, exp=0.95, PF=1.05.

### structure_shift

- `False` — long n=216, exp=-0.55, PF=0.97; short n=164, exp=-2.36, PF=0.88.
- `True` — long n=437, exp=4.66, PF=1.27; short n=401, exp=1.60, PF=1.09.

### fvg_context

- `False` — long n=560, exp=2.19, PF=1.13; short n=483, exp=-0.91, PF=0.95.
- `True` — long n=93, exp=7.40, PF=1.45; short n=82, exp=8.48, PF=1.50.

### htf_alignment

- `aligned` — long n=608, exp=3.36, PF=1.20; short n=511, exp=0.73, PF=1.04.
- `neutral/unknown` — long n=45, exp=-2.73, PF=0.85; short n=54, exp=-2.22, PF=0.88.

### time_bucket

- `10:30+` — long n=653, exp=2.94, PF=1.17; short n=565, exp=0.45, PF=1.02.

## SNR / RVOL diagnostics

- snr_1m: long mean 1.94 / median 1.81 (n=653); short mean 1.90 / median 1.80 (n=565).
- snr_5m: long mean 1.79 / median 1.61 (n=653); short mean 1.61 / median 1.32 (n=565).
- snr_15m: long mean 1.97 / median 1.74 (n=653); short mean 2.11 / median 1.76 (n=565).
- rvol_rolling: long mean 2.63 / median 1.73 (n=653); short mean 2.71 / median 1.73 (n=565).
- rvol_time_of_day: long mean 1.40 / median 1.31 (n=644); short mean 1.39 / median 1.32 (n=552).

## Diagnostic flags

- Direction gap has the aggregate sign in **2/3 years**.
- High-score (80+) short sample: **116 trades**.
- Evidence for later separate scoring: **candidate** (diagnostic flag only; no config split authorized).
- Treat categorical cells under 30 trades and numeric quartiles under 30 trades as exploratory; direction-level conclusions should also be checked for year stability.
