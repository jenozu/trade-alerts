# R4.4 — Candidate Scoring Models

Offline calibration research only.

Production `strategy.yaml` was not changed.

## Baseline reconstruction

- MAE: 0.000
- Median absolute error: 0.000
- Maximum absolute error: 0.000
- Within 1 point: 100.0%

## Candidate weights

### baseline

- higher_timeframe_bias: 10
- draw_on_liquidity: 10
- key_location: 8
- liquidity_sweep: 14
- displacement: 12
- structure_shift: 12
- fvg_or_retest: 8
- relative_volume: 6
- signal_to_noise: 10
- premium_discount: 4
- room_to_target: 6

### candidate_conservative

- higher_timeframe_bias: 12
- draw_on_liquidity: 10
- key_location: 8
- liquidity_sweep: 10
- displacement: 14
- structure_shift: 14
- fvg_or_retest: 10
- relative_volume: 6
- signal_to_noise: 7
- premium_discount: 3
- room_to_target: 6

### candidate_evidence_tilt

- higher_timeframe_bias: 13
- draw_on_liquidity: 9
- key_location: 8
- liquidity_sweep: 8
- displacement: 16
- structure_shift: 16
- fvg_or_retest: 12
- relative_volume: 6
- signal_to_noise: 5
- premium_discount: 2
- room_to_target: 5

### candidate_redundancy_reduced

- higher_timeframe_bias: 11
- draw_on_liquidity: 8
- key_location: 8
- liquidity_sweep: 8
- displacement: 18
- structure_shift: 18
- fvg_or_retest: 12
- relative_volume: 7
- signal_to_noise: 4
- premium_discount: 2
- room_to_target: 4

## Existing-baseline threshold diagnostics

| Model | Threshold | Trades | Exp pts | Exp R | PF | Win | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 70 | 1218 | 1.78 | 0.071 | 1.10 | 27.8% | 2172.50 | 47.1% | 32.8% | 21.8% | 14.6% | 70.5% |
| baseline | 80 | 260 | 5.33 | 0.212 | 1.30 | 28.1% | 1384.50 | 46.5% | 34.6% | 24.2% | 20.0% | 71.2% |
| baseline | 90 | 21 | 13.70 | 0.548 | 1.88 | 38.1% | 287.75 | 57.1% | 52.4% | 28.6% | 23.8% | 61.9% |
| candidate_conservative | 70 | 1124 | 1.83 | 0.073 | 1.10 | 27.7% | 2059.00 | 47.0% | 32.8% | 21.7% | 14.9% | 70.7% |
| candidate_conservative | 80 | 295 | 5.07 | 0.201 | 1.29 | 29.2% | 1495.75 | 48.1% | 34.6% | 23.4% | 18.6% | 70.2% |
| candidate_conservative | 90 | 28 | 7.79 | 0.312 | 1.45 | 32.1% | 218.25 | 50.0% | 46.4% | 25.0% | 17.9% | 67.9% |
| candidate_evidence_tilt | 70 | 1003 | 2.35 | 0.094 | 1.13 | 28.0% | 2356.50 | 47.4% | 33.5% | 22.0% | 15.4% | 70.5% |
| candidate_evidence_tilt | 80 | 377 | 7.07 | 0.281 | 1.41 | 31.6% | 2665.75 | 48.5% | 35.0% | 24.7% | 19.9% | 67.9% |
| candidate_evidence_tilt | 90 | 70 | 12.94 | 0.517 | 1.80 | 35.7% | 905.75 | 54.3% | 47.1% | 30.0% | 24.3% | 64.3% |
| candidate_redundancy_reduced | 70 | 935 | 2.27 | 0.090 | 1.13 | 27.9% | 2120.75 | 47.3% | 33.5% | 22.0% | 15.5% | 70.7% |
| candidate_redundancy_reduced | 80 | 368 | 5.72 | 0.227 | 1.33 | 30.2% | 2106.75 | 47.8% | 34.2% | 24.2% | 19.3% | 69.3% |
| candidate_redundancy_reduced | 90 | 84 | 15.86 | 0.637 | 2.02 | 38.1% | 1332.50 | 56.0% | 48.8% | 31.0% | 25.0% | 61.9% |

## Critical limitation

These diagnostics re-score only the trades that survived the historical baseline model.

They do **not** show the true performance of the candidate models because changing weights would also change which historical setups became eligible for entry.

The candidate models must therefore be tested next against the full scored historical feature universe using the normal causal backtest path.

**No production score-weight changes are authorized by R4.4.**