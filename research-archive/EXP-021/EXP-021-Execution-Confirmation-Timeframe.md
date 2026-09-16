# EXP-021 — Execution / Confirmation Timeframe

Diagnostic only.

## Coverage

- Feature matched: 1218 / 1218

## Break mode

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Avg MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| neither | 659 | 26.1% | 0.05 | 0.003 | 1.00 | 35.25 | 45.2% | 31.7% | 20.9% | 13.2% | 72.1% | — | — |
| close_and_wick | 518 | 29.9% | 3.99 | 0.159 | 1.23 | 2065.50 | 48.8% | 34.0% | 22.6% | 16.6% | 68.5% | — | — |
| wick_only | 41 | 26.8% | 1.75 | 0.065 | 1.10 | 71.75 | 56.1% | 34.1% | 26.8% | 12.2% | 70.7% | — | — |

## Structure-break confirmation type

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Avg MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| none | 827 | 27.1% | 1.23 | 0.050 | 1.07 | 1021.25 | 46.3% | 33.4% | 21.8% | 13.9% | 71.3% | — | — |
| displacement | 245 | 31.8% | 5.36 | 0.212 | 1.32 | 1313.50 | 49.4% | 33.9% | 24.1% | 17.6% | 67.3% | — | — |
| body_close | 146 | 24.7% | -1.11 | -0.043 | 0.94 | -162.25 | 47.9% | 27.4% | 18.5% | 13.7% | 71.2% | — | — |

## Confirmation availability delay

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Avg MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| unknown | 827 | 27.1% | 1.23 | 0.050 | 1.07 | 1021.25 | 46.3% | 33.4% | 21.8% | 13.9% | 71.3% | — | — |
| 0-1m | 391 | 29.2% | 2.94 | 0.117 | 1.17 | 1151.25 | 48.8% | 31.5% | 22.0% | 16.1% | 68.8% | — | — |

## Structure reclaim

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Avg MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 1200 | 27.5% | 1.55 | 0.062 | 1.09 | 1861.00 | 46.8% | 32.5% | 21.5% | 14.6% | 70.8% | — | — |
| True | 18 | 44.4% | 17.31 | 0.700 | 2.24 | 311.50 | 66.7% | 50.0% | 44.4% | 16.7% | 55.6% | — | — |

## FVG first-touch / retest-hold state

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Avg MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| neither | 1144 | 27.8% | 1.83 | 0.073 | 1.10 | 2089.00 | 47.1% | 32.9% | 21.9% | 14.7% | 70.4% | — | — |
| first_touch_and_hold | 55 | 27.3% | 0.43 | 0.014 | 1.02 | 23.75 | 47.3% | 30.9% | 18.2% | 12.7% | 72.7% | — | — |
| first_touch_only | 19 | 26.3% | 3.14 | 0.124 | 1.17 | 59.75 | 47.4% | 31.6% | 26.3% | 15.8% | 73.7% | — | — |

## Directional entry-valid state

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Avg MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| False | 1200 | 27.9% | 2.00 | 0.080 | 1.11 | 2398.75 | 47.4% | 33.0% | 22.0% | 14.8% | 70.3% | — | — |
| True | 18 | 16.7% | -12.57 | -0.512 | 0.40 | -226.25 | 27.8% | 16.7% | 11.1% | 0.0% | 83.3% | — | — |

## Entry-valid family

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Avg MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| neither | 1200 | 27.9% | 2.00 | 0.080 | 1.11 | 2398.75 | 47.4% | 33.0% | 22.0% | 14.8% | 70.3% | — | — |
| both | 8 | 12.5% | -16.91 | -0.696 | 0.22 | -135.25 | 12.5% | 12.5% | 12.5% | 0.0% | 87.5% | — | — |
| continuation | 8 | 25.0% | -5.06 | -0.203 | 0.73 | -40.50 | 37.5% | 25.0% | 12.5% | 0.0% | 75.0% | — | — |
| reversal | 2 | 0.0% | -25.25 | -1.010 | 0.00 | -50.50 | 50.0% | 0.0% | 0.0% | 0.0% | 100.0% | — | — |

## Limitations

- EXP-021 analyzes confirmation states attached to the existing baseline trades.
- It does not reconstruct hypothetical alternative fills for an earlier immediate entry or a later confirmation entry.
- Therefore performance differences are diagnostic associations, not counterfactual execution simulations.
- Any actual change to entry timing requires a later dedicated backtest with alternate fills and identical stop/target rules.

## Decision

**Diagnostic only — no strategy change.**