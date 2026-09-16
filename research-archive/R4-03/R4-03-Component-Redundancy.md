# R4.3 — Score Component Redundancy

Diagnostic calibration research only.

- Baseline trades: 1218

## Strongest activation relationships

| A | B | Phi | Jaccard | Both n | A when B | B when A | Both Exp | A-only Exp | B-only Exp |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| room_to_target | penalty_major_obstacle | -1.00 | 0.00 | 0 | 0.0% | 0.0% | — | 1.58 | 18.18 |
| displacement | premium_discount | -0.38 | 0.39 | 465 | 60.3% | 52.2% | 1.52 | 4.13 | -1.21 |
| liquidity_sweep | signal_to_noise | -0.32 | 0.22 | 256 | 67.9% | 24.8% | -0.47 | 1.54 | 3.81 |
| liquidity_sweep | premium_discount | 0.29 | 0.66 | 715 | 92.7% | 69.2% | -0.03 | 3.45 | 6.38 |
| liquidity_sweep | structure_shift | -0.26 | 0.54 | 658 | 78.5% | 63.7% | 2.40 | -1.34 | 6.10 |
| structure_shift | premium_discount | -0.23 | 0.41 | 468 | 60.7% | 55.8% | 0.44 | 6.68 | 0.43 |
| signal_to_noise | penalty_snr_conflict | -0.20 | 0.00 | 0 | 0.0% | 0.0% | — | 0.90 | -6.15 |
| structure_shift | penalty_snr_conflict | 0.19 | 0.12 | 99 | 99.0% | 11.8% | -6.72 | 4.52 | 50.25 |
| higher_timeframe_bias | displacement | -0.17 | 0.65 | 793 | 89.0% | 70.9% | 3.39 | -0.84 | -2.27 |
| signal_to_noise | penalty_major_obstacle | 0.17 | 0.04 | 15 | 100.0% | 4.0% | 18.18 | 0.19 | — |
| signal_to_noise | room_to_target | -0.17 | 0.30 | 362 | 30.1% | 96.0% | 0.19 | 18.18 | 2.18 |
| structure_shift | signal_to_noise | -0.16 | 0.22 | 217 | 57.6% | 25.9% | 4.82 | 2.63 | -4.41 |
| displacement | signal_to_noise | -0.15 | 0.23 | 238 | 63.1% | 26.7% | 2.87 | 2.73 | -2.47 |
| higher_timeframe_bias | structure_shift | -0.14 | 0.62 | 748 | 89.3% | 66.8% | 3.92 | -1.38 | -2.79 |
| structure_shift | relative_volume | -0.13 | 0.52 | 605 | 65.3% | 72.2% | 3.35 | 2.79 | -1.04 |
| premium_discount | relative_volume | -0.13 | 0.48 | 553 | 59.7% | 71.7% | -0.02 | 1.60 | 4.57 |
| relative_volume | signal_to_noise | -0.13 | 0.24 | 255 | 67.6% | 27.5% | 0.86 | 2.20 | 1.00 |
| premium_discount | room_to_target | 0.13 | 0.64 | 770 | 64.0% | 99.9% | 0.47 | -25.25 | 3.55 |
| premium_discount | penalty_major_obstacle | -0.13 | 0.00 | 1 | 6.7% | 0.1% | -25.25 | 0.47 | 21.29 |
| draw_on_liquidity | signal_to_noise | -0.13 | 0.30 | 357 | 94.7% | 30.0% | 1.72 | 1.87 | -13.74 |
| liquidity_sweep | penalty_snr_conflict | 0.13 | 0.10 | 100 | 100.0% | 9.7% | -6.15 | 1.81 | — |
| displacement | structure_shift | -0.11 | 0.51 | 586 | 69.9% | 65.8% | 5.06 | -1.64 | -1.15 |
| liquidity_sweep | displacement | -0.11 | 0.62 | 735 | 82.5% | 71.2% | 1.60 | -0.33 | 8.29 |
| fvg_or_retest | premium_discount | -0.10 | 0.58 | 699 | 90.7% | 62.0% | 0.33 | 5.07 | 1.48 |
| structure_shift | fvg_or_retest | -0.10 | 0.63 | 762 | 67.6% | 90.9% | 3.56 | -0.46 | -0.84 |
| higher_timeframe_bias | liquidity_sweep | -0.08 | 0.78 | 940 | 91.0% | 84.0% | 1.39 | 6.21 | -2.44 |
| displacement | penalty_snr_conflict | -0.08 | 0.07 | 62 | 62.0% | 7.0% | -6.89 | 3.49 | -4.94 |
| structure_shift | room_to_target | -0.08 | 0.68 | 823 | 68.4% | 98.2% | 2.92 | 18.18 | -1.33 |
| structure_shift | penalty_major_obstacle | 0.08 | 0.02 | 15 | 100.0% | 1.8% | 18.18 | 2.92 | — |
| higher_timeframe_bias | fvg_or_retest | -0.07 | 0.85 | 1030 | 91.3% | 92.0% | 2.55 | -2.38 | -2.27 |

## Interpretation

- High activation correlation alone does not prove two components are redundant.
- Redundancy is more credible when activation overlap is high AND the second component adds little incremental expectancy/PF when the first is already present.
- A correlated pair can still deserve separate scoring if the combined state materially outperforms either component alone.
- Sparse penalties and rare components must not drive weight changes.

## Calibration rule

Do not alter score weights from R4.3 alone. Combine these results with R4.2 realized lift and EXP-001 through EXP-021 evidence.