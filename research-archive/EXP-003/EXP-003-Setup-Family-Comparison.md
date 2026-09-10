# EXP-003 — Setup-Family Comparison

Ledger-only diagnostic. No historical pipeline rerun and no strategy/scoring changes.

## Classification contract

- Rule: `reversal if directional liquidity_sweep context is true; otherwise continuation`.
- This is the existing production planner family-selection contract, not a new research heuristic.
- Explicit-family years: none.
- Ledger-derived years: [2023, 2024, 2025].

## Inputs

- 2023: `/docker/trade-alerts-2023/data/results/backtest/trades.csv`
- 2024: `/docker/trade-alerts-2024/data/results/backtest/trades.csv`
- 2025: `/docker/trade-alerts/data/results/research_runs/2025_pipeline_final/backtest/trades.csv`

## Overall

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Med MFE | Avg MAE | Med MAE | Avg hold |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| REVERSAL | 1033 | 27.2% | 1.04 | 0.042 | 1.06 | 1076.25 | 46.1% | 32.4% | 21.2% | 13.6% | 71.0% | 38.71 | 22.00 | 27.23 | 27.50 | 18.72 |
| CONTINUATION | 185 | 30.8% | 5.93 | 0.234 | 1.34 | 1096.25 | 53.0% | 34.6% | 25.4% | 20.5% | 68.1% | 43.70 | 28.75 | 26.17 | 27.00 | 16.83 |

## Year-by-year

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Med MFE | Avg MAE | Med MAE | Avg hold |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2023 reversal | 298 | 32.2% | 2.79 | 0.113 | 1.17 | 830.00 | 52.0% | 35.2% | 21.5% | 11.4% | 65.8% | 39.81 | 28.25 | 24.48 | 26.50 | 23.55 |
| 2023 continuation | 46 | 32.6% | 3.76 | 0.146 | 1.22 | 173.00 | 47.8% | 30.4% | 19.6% | 15.2% | 67.4% | 39.17 | 23.00 | 24.35 | 26.75 | 24.74 |
| 2024 reversal | 328 | 25.6% | -1.61 | -0.063 | 0.91 | -526.50 | 43.3% | 30.2% | 19.2% | 10.7% | 72.3% | 35.80 | 20.50 | 25.96 | 27.12 | 20.71 |
| 2024 continuation | 60 | 36.7% | 9.88 | 0.391 | 1.63 | 592.75 | 50.0% | 35.0% | 30.0% | 23.3% | 61.7% | 43.18 | 22.38 | 24.60 | 25.62 | 18.17 |
| 2025 reversal | 407 | 24.8% | 1.90 | 0.075 | 1.10 | 772.75 | 44.0% | 32.2% | 22.6% | 17.4% | 73.7% | 40.25 | 21.25 | 30.26 | 28.75 | 13.58 |
| 2025 continuation | 79 | 25.3% | 4.18 | 0.167 | 1.22 | 330.50 | 58.2% | 36.7% | 25.3% | 21.5% | 73.4% | 46.72 | 35.75 | 28.41 | 30.25 | 11.22 |

## Long vs short within family

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Med MFE | Avg MAE | Med MAE | Avg hold |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| LONG reversal | 578 | 29.9% | 3.12 | 0.126 | 1.18 | 1804.50 | 47.1% | 34.8% | 22.5% | 13.5% | 68.2% | 39.85 | 23.50 | 27.16 | 27.00 | 20.44 |
| LONG continuation | 75 | 29.3% | 1.51 | 0.056 | 1.09 | 113.00 | 50.7% | 29.3% | 21.3% | 16.0% | 69.3% | 39.52 | 25.25 | 28.41 | 27.75 | 18.76 |
| SHORT reversal | 455 | 23.7% | -1.60 | -0.064 | 0.91 | -728.25 | 44.8% | 29.5% | 19.6% | 13.6% | 74.5% | 37.26 | 20.25 | 27.32 | 27.50 | 16.55 |
| SHORT continuation | 110 | 31.8% | 8.94 | 0.356 | 1.52 | 983.25 | 54.5% | 38.2% | 28.2% | 23.6% | 67.3% | 46.54 | 35.50 | 24.64 | 26.50 | 15.52 |

## Score distribution

- reversal: n=1033, mean=76.22, median=74.58, std=5.44, bands={'70-79': 798, '80-89': 214, '90-100': 21}.
- continuation: n=185, mean=73.24, median=71.82, std=3.59, bands={'70-79': 160, '80-89': 25}.

## Score-band performance

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Med MFE | Avg MAE | Med MAE | Avg hold |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 70-79 reversal | 798 | 27.2% | 0.11 | 0.005 | 1.01 | 90.75 | 46.2% | 31.8% | 20.6% | 11.9% | 70.7% | 38.45 | 22.25 | 26.98 | 27.50 | 19.53 |
| 70-79 continuation | 160 | 30.0% | 4.36 | 0.171 | 1.25 | 697.25 | 52.5% | 34.4% | 24.4% | 19.4% | 68.8% | 43.13 | 28.38 | 26.50 | 27.38 | 16.62 |
| 80-89 reversal | 214 | 26.2% | 3.26 | 0.129 | 1.18 | 697.75 | 44.4% | 32.7% | 22.9% | 18.7% | 72.9% | 38.32 | 18.75 | 27.91 | 27.00 | 15.86 |
| 80-89 continuation | 25 | 36.0% | 15.96 | 0.638 | 1.99 | 399.00 | 56.0% | 36.0% | 32.0% | 28.0% | 64.0% | 47.32 | 41.75 | 24.02 | 26.00 | 18.20 |
| 90-100 reversal | 21 | 38.1% | 13.70 | 0.548 | 1.88 | 287.75 | 57.1% | 52.4% | 28.6% | 23.8% | 61.9% | 52.74 | 54.75 | 29.75 | 26.75 | 17.10 |
| 90-100 continuation | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

## Context diagnostics

### displacement

- `False` — reversal n=298, exp=-3.43, PF=0.82; continuation n=30, exp=7.37, PF=1.42.
- `True` — reversal n=735, exp=2.85, PF=1.16; continuation n=155, exp=5.65, PF=1.33.

### structure_shift

- `False` — reversal n=375, exp=-1.34, PF=0.93; continuation n=5, exp=-0.25, PF=0.99.
- `True` — reversal n=658, exp=2.40, PF=1.13; continuation n=180, exp=6.10, PF=1.35.

### fvg_context

- `False` — reversal n=870, exp=-0.19, PF=0.99; continuation n=173, exp=5.53, PF=1.32.
- `True` — reversal n=163, exp=7.63, PF=1.46; continuation n=12, exp=11.65, PF=1.69.

### htf_bias

- `bearish` — reversal n=404, exp=-1.38, PF=0.93; continuation n=107, exp=8.73, PF=1.51.
- `bullish` — reversal n=536, exp=3.47, PF=1.20; continuation n=72, exp=2.48, PF=1.14.
- `neutral` — reversal n=93, exp=-2.44, PF=0.87; continuation n=6, exp=-2.67, PF=0.86.

### dol_direction

- `bearish` — reversal n=449, exp=-1.84, PF=0.90; continuation n=110, exp=8.94, PF=1.52.
- `bullish` — reversal n=560, exp=3.18, PF=1.18; continuation n=71, exp=3.01, PF=1.18.
- `neutral` — reversal n=24, exp=5.21, PF=1.28; continuation n=4, exp=-25.25, PF=0.00.

### htf_alignment

- `aligned` — reversal n=940, exp=1.39, PF=1.08; continuation n=179, exp=6.21, PF=1.36.
- `neutral/unknown` — reversal n=93, exp=-2.44, PF=0.87; continuation n=6, exp=-2.67, PF=0.86.

### time_bucket

- `10:30+` — reversal n=1033, exp=1.04, PF=1.06; continuation n=185, exp=5.93, PF=1.34.

## SNR / RVOL diagnostics

- snr_1m: reversal mean 1.83 / median 1.73 (n=1033); continuation mean 2.44 / median 2.28 (n=185).
- snr_5m: reversal mean 1.61 / median 1.37 (n=1033); continuation mean 2.26 / median 2.14 (n=185).
- snr_15m: reversal mean 1.91 / median 1.59 (n=1033); continuation mean 2.74 / median 2.50 (n=185).
- rvol_rolling: reversal mean 2.64 / median 1.72 (n=1033); continuation mean 2.83 / median 1.78 (n=185).
- rvol_time_of_day: reversal mean 1.37 / median 1.28 (n=1013); continuation mean 1.53 / median 1.50 (n=183).

## Capability / limitation flags

- Level type available in ledger: **False**.
- Explicit volatility regime available in ledger: **False**.
- Acceptance detail available in ledger: **False**.
- Retest-quality detail available in ledger: **False**.
- BOS separately available in ledger: **False**.
- MSS/CHOCH separately available in ledger: **False**.
- If these are false, EXP-003 must not invent those sub-classifications; later component experiments can use richer scored/structure artifacts.

## Sample-size discipline

- Treat categorical cells under 30 trades and numeric quartiles under 30 trades as exploratory. Family-level conclusions must also be checked across years and directions.
