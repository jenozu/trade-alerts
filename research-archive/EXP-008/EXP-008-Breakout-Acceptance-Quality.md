# EXP-008 — Breakout / Acceptance Quality

Diagnostic analysis of existing continuation trades only.

## Coverage

- Baseline trades: 1218
- Continuation trades: 185
- Feature matched: 185

## Directional 1m close break

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 47 | 29.8% | 4.60 | 0.181 | 1.26 | 216.25 | 51.1% | 34.0% | 27.7% | 21.3% | 70.2% |
| True | 138 | 31.2% | 6.38 | 0.252 | 1.37 | 880.00 | 53.6% | 34.8% | 24.6% | 20.3% | 67.4% |

## Directional wick break

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 47 | 29.8% | 4.60 | 0.181 | 1.26 | 216.25 | 51.1% | 34.0% | 27.7% | 21.3% | 70.2% |
| True | 138 | 31.2% | 6.38 | 0.252 | 1.37 | 880.00 | 53.6% | 34.8% | 24.6% | 20.3% | 67.4% |

## Stored break confirmation

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| <missing> | 117 | 28.2% | 2.83 | 0.111 | 1.16 | 331.25 | 48.7% | 35.0% | 23.9% | 18.8% | 71.8% |
| body_close | 17 | 47.1% | 29.13 | 1.161 | 3.29 | 495.25 | 76.5% | 52.9% | 41.2% | 35.3% | 47.1% |
| displacement | 51 | 31.4% | 5.29 | 0.209 | 1.31 | 269.75 | 54.9% | 27.5% | 23.5% | 19.6% | 66.7% |

## Completed 5m close beyond broken level

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 163 | 30.1% | 4.68 | 0.184 | 1.27 | 762.50 | 52.1% | 33.7% | 23.9% | 19.6% | 68.7% |
| True | 22 | 36.4% | 15.17 | 0.607 | 1.94 | 333.75 | 59.1% | 40.9% | 36.4% | 27.3% | 63.6% |

## Retest present before signal

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 185 | 30.8% | 5.93 | 0.234 | 1.34 | 1096.25 | 53.0% | 34.6% | 25.4% | 20.5% | 68.1% |

## Retest hold before signal

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 185 | 30.8% | 5.93 | 0.234 | 1.34 | 1096.25 | 53.0% | 34.6% | 25.4% | 20.5% | 68.1% |

## Break displacement category

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| <missing> | 117 | 28.2% | 2.83 | 0.111 | 1.16 | 331.25 | 48.7% | 35.0% | 23.9% | 18.8% | 71.8% |
| moderate | 11 | 63.6% | 46.45 | 1.858 | 6.06 | 511.00 | 81.8% | 72.7% | 54.5% | 45.5% | 36.4% |
| strong | 51 | 31.4% | 5.29 | 0.209 | 1.31 | 269.75 | 54.9% | 27.5% | 23.5% | 19.6% | 66.7% |
| weak | 6 | 16.7% | -2.62 | -0.118 | 0.86 | -15.75 | 66.7% | 16.7% | 16.7% | 16.7% | 66.7% |

## Broken structure timeframe

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1m | 68 | 35.3% | 11.25 | 0.447 | 1.70 | 765.00 | 60.3% | 33.8% | 27.9% | 23.5% | 61.8% |
| <missing> | 117 | 28.2% | 2.83 | 0.111 | 1.16 | 331.25 | 48.7% | 35.0% | 23.9% | 18.8% | 71.8% |

## Break-to-signal delay quartiles

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| nan | 185 | 30.8% | 5.93 | 0.234 | 1.34 | 1096.25 | 53.0% | 34.6% | 25.4% | 20.5% | 68.1% |

## Pre-entry follow-through quartiles

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| (1.749, 9.5] | 18 | 44.4% | 21.22 | 0.837 | 2.60 | 382.00 | 66.7% | 38.9% | 33.3% | 27.8% | 50.0% |
| (15.0, 22.75] | 18 | 33.3% | 12.81 | 0.512 | 1.79 | 230.50 | 55.6% | 38.9% | 33.3% | 27.8% | 61.1% |
| (22.75, 40.75] | 16 | 31.2% | 13.81 | 0.553 | 1.80 | 221.00 | 68.8% | 37.5% | 31.2% | 31.2% | 68.8% |
| (9.5, 15.0] | 16 | 31.2% | -4.28 | -0.171 | 0.75 | -68.50 | 50.0% | 18.8% | 12.5% | 6.2% | 68.8% |
| nan | 117 | 28.2% | 2.83 | 0.111 | 1.16 | 331.25 | 48.7% | 35.0% | 23.9% | 18.8% | 71.8% |

## Break displacement-score quartiles

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| (52.729, 75.981] | 17 | 47.1% | 29.13 | 1.161 | 3.29 | 495.25 | 76.5% | 52.9% | 41.2% | 35.3% | 47.1% |
| (75.981, 85.101] | 17 | 29.4% | 0.99 | 0.035 | 1.06 | 16.75 | 64.7% | 35.3% | 23.5% | 11.8% | 70.6% |
| (85.101, 88.435] | 17 | 35.3% | 14.04 | 0.562 | 1.89 | 238.75 | 64.7% | 29.4% | 29.4% | 29.4% | 58.8% |
| (88.435, 100.0] | 17 | 29.4% | 0.84 | 0.031 | 1.05 | 14.25 | 35.3% | 17.6% | 17.6% | 17.6% | 70.6% |
| nan | 117 | 28.2% | 2.83 | 0.111 | 1.16 | 331.25 | 48.7% | 35.0% | 23.9% | 18.8% | 71.8% |

## Break RVOL quartiles

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| (0.11699999999999999, 1.274] | 17 | 23.5% | -2.68 | -0.115 | 0.86 | -45.50 | 47.1% | 23.5% | 11.8% | 11.8% | 70.6% |
| (1.274, 1.635] | 17 | 35.3% | 19.60 | 0.779 | 2.26 | 333.25 | 64.7% | 47.1% | 41.2% | 35.3% | 58.8% |
| (1.635, 2.037] | 17 | 41.2% | 12.50 | 0.500 | 1.84 | 212.50 | 82.4% | 35.3% | 29.4% | 23.5% | 58.8% |
| (2.037, 2.955] | 17 | 41.2% | 15.57 | 0.623 | 2.05 | 264.75 | 47.1% | 29.4% | 29.4% | 23.5% | 58.8% |
| nan | 117 | 28.2% | 2.83 | 0.111 | 1.16 | 331.25 | 48.7% | 35.0% | 23.9% | 18.8% | 71.8% |

## Year diagnostics

### 2023

#### Close break

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 17 | 23.5% | -6.34 | -0.259 | 0.67 | -107.75 | 35.3% | 23.5% | 17.6% | 11.8% | 76.5% |
| True | 29 | 37.9% | 9.68 | 0.383 | 1.62 | 280.75 | 55.2% | 34.5% | 20.7% | 17.2% | 62.1% |

#### Completed 5m close

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 39 | 30.8% | 2.19 | 0.082 | 1.13 | 85.50 | 46.2% | 30.8% | 17.9% | 15.4% | 69.2% |
| True | 7 | 42.9% | 12.50 | 0.500 | 1.87 | 87.50 | 57.1% | 28.6% | 28.6% | 14.3% | 57.1% |

#### Retest hold

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 46 | 32.6% | 3.76 | 0.146 | 1.22 | 173.00 | 47.8% | 30.4% | 19.6% | 15.2% | 67.4% |

### 2024

#### Close break

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 14 | 42.9% | 16.21 | 0.649 | 2.12 | 227.00 | 57.1% | 50.0% | 42.9% | 28.6% | 57.1% |
| True | 46 | 34.8% | 7.95 | 0.313 | 1.49 | 365.75 | 47.8% | 30.4% | 26.1% | 21.7% | 63.0% |

#### Completed 5m close

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 54 | 37.0% | 9.15 | 0.361 | 1.59 | 494.25 | 50.0% | 35.2% | 29.6% | 22.2% | 61.1% |
| True | 6 | 33.3% | 16.42 | 0.657 | 1.98 | 98.50 | 50.0% | 33.3% | 33.3% | 33.3% | 66.7% |

#### Retest hold

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 60 | 36.7% | 9.88 | 0.391 | 1.63 | 592.75 | 50.0% | 35.0% | 30.0% | 23.3% | 61.7% |

### 2025

#### Close break

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 16 | 25.0% | 6.06 | 0.240 | 1.32 | 97.00 | 62.5% | 31.2% | 25.0% | 25.0% | 75.0% |
| True | 63 | 25.4% | 3.71 | 0.148 | 1.20 | 233.50 | 57.1% | 38.1% | 25.4% | 20.6% | 73.0% |

#### Completed 5m close

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 70 | 24.3% | 2.61 | 0.104 | 1.14 | 182.75 | 57.1% | 34.3% | 22.9% | 20.0% | 74.3% |
| True | 9 | 33.3% | 16.42 | 0.657 | 1.98 | 147.75 | 66.7% | 55.6% | 44.4% | 33.3% | 66.7% |

#### Retest hold

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 79 | 25.3% | 4.18 | 0.167 | 1.22 | 330.50 | 58.2% | 36.7% | 25.3% | 21.5% | 73.4% |

## Operational definitions / limitations

- EXP-008 analyzes the existing continuation subset; it does not create new trades.
- `retest_present` is derived deterministically from a post-break revisit of `structure_broken_level` before signal time.
- `retest_hold` requires the post-touch closes through signal time to remain on the accepted side of the broken level.
- `completed_5m_close_beyond` uses only completed five-minute closes available by signal time.
- These derived diagnostics are research labels, not new production entry rules.
- No missed-trade opportunity cost can be measured without rerunning alternative entry logic; EXP-008 therefore does not pretend that it can.
- Small cells remain exploratory.

## Decision discipline

**Diagnostic only — no strategy change.**