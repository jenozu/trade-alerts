# F012 — Continuation outperforms reversal across years

Status: Supported

Source: [[../Experiments/EXP-003-Setup-Family-Comparison]]

## Finding

The continuation-classified setup family materially outperforms the reversal-classified family in aggregate and has higher expectancy and profit factor in each of the 2023, 2024, and 2025 baseline years.

## Evidence

Overall:

- Reversal: 1,033 trades, +1.04 pts expectancy, +0.042R, PF 1.06, +1,076.25 net points.
- Continuation: 185 trades, +5.93 pts expectancy, +0.234R, PF 1.34, +1,096.25 net points.

Year by year:

- 2023 reversal: +2.79 pts, PF 1.17; continuation: +3.76 pts, PF 1.22.
- 2024 reversal: -1.61 pts, PF 0.91; continuation: +9.88 pts, PF 1.63.
- 2025 reversal: +1.90 pts, PF 1.10; continuation: +4.18 pts, PF 1.22.

Continuation therefore has the stronger expectancy/PF in all three years, though the magnitude of the gap is regime-dependent and largest in 2024.

## Important direction interaction

The aggregate family advantage is not universal within direction:

- LONG reversal: +3.12 pts, PF 1.18.
- LONG continuation: +1.51 pts, PF 1.09.
- SHORT reversal: -1.60 pts, PF 0.91.
- SHORT continuation: +8.94 pts, PF 1.52.

This means the overall continuation advantage is heavily influenced by short-side behavior and should not be converted directly into a blanket production preference for continuation setups.

## Limitation

The archived ledger lacks an explicit setup-family field. EXP-003 deterministically projects the existing planner family-selection contract using the persisted directional `liquidity_sweep` context. The continuation bucket therefore identifies the planner's non-reversal family choice, not independently verified completion of every acceptance/retest/BOS state-machine step.

## Implication

Continuation deserves explicit preservation and deeper component study. Reversal should be decomposed rather than discarded, especially because long reversals remain profitable. No production setup-family filter or config split is authorized by EXP-003 alone.
