# R4.2 — Score Component Lift Analysis

Diagnostic calibration research only.

## Coverage

- Matched baseline trades: 1218 / 1218

## Aggregate component lift

| Component | With n | Without n | With Exp | Without Exp | Exp Lift | With PF | Without PF | PF Lift |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| penalty_major_obstacle | 15 | 1203 | 18.18 | 1.58 | 16.60 | 2.20 | 1.09 | 1.11 |
| fvg_or_retest | 1128 | 90 | 2.13 | -2.58 | 4.71 | 1.12 | 0.86 | 0.26 |
| higher_timeframe_bias | 1119 | 99 | 2.16 | -2.45 | 4.61 | 1.12 | 0.87 | 0.25 |
| structure_shift | 838 | 380 | 3.20 | -1.33 | 4.53 | 1.18 | 0.93 | 0.25 |
| displacement | 891 | 327 | 2.77 | -0.90 | 3.67 | 1.16 | 0.95 | 0.21 |
| draw_on_liquidity | 1189 | 29 | 1.83 | -0.04 | 1.87 | 1.10 | 1.00 | 0.10 |
| relative_volume | 926 | 292 | 1.83 | 1.64 | 0.19 | 1.10 | 1.09 | 0.01 |
| signal_to_noise | 377 | 841 | 0.90 | 2.18 | -1.27 | 1.05 | 1.12 | -0.07 |
| premium_discount | 771 | 447 | 0.44 | 4.11 | -3.67 | 1.02 | 1.24 | -0.21 |
| liquidity_sweep | 1033 | 185 | 1.04 | 5.93 | -4.88 | 1.06 | 1.34 | -0.28 |
| penalty_snr_conflict | 100 | 1118 | -6.15 | 2.49 | -8.64 | 0.68 | 1.14 | -0.46 |
| room_to_target | 1203 | 15 | 1.58 | 18.18 | -16.60 | 1.09 | 2.20 | -1.11 |
| key_location | 1218 | 0 | 1.78 | — | — | 1.10 | — | — |
| penalty_data_quality | 0 | 1218 | — | 1.78 | — | — | 1.10 | — |
| penalty_failed_retest | 0 | 1218 | — | 1.78 | — | — | 1.10 | — |
| penalty_htf_conflict | 0 | 1218 | — | 1.78 | — | — | 1.10 | — |
| penalty_stale_setup | 0 | 1218 | — | 1.78 | — | — | 1.10 | — |

## Interpretation limits

- These are realized associations inside the surviving historical baseline trades.
- Components already participate in historical scoring, so component presence is selection-confounded.
- Lift does not prove causal value.
- A component with positive aggregate lift can still be unstable across years or setup families.
- Penalty fields require special interpretation because surviving trades may represent only cases where the overall score remained high enough despite the penalty.

## Next step

Use the year/family/direction stability results from this analysis together with the completed EXP-001 through EXP-021 evidence before R4.3 redundancy analysis.

**No score-weight changes are authorized by R4.2 alone.**