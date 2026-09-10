# F011 — Reversal quality depends on confirmation context

Status: Supported

Source: [[../Experiments/EXP-003-Setup-Family-Comparison]]

## Finding

Within the reversal-classified baseline trades, displacement and FVG context materially separate profitable from weak reversal performance.

## Evidence

Displacement split:

- Reversal without displacement: 298 trades, -3.43 pts expectancy, PF 0.82.
- Reversal with displacement: 735 trades, +2.85 pts expectancy, PF 1.16.

FVG-context split:

- Reversal without FVG context: 870 trades, -0.19 pts expectancy, PF 0.99.
- Reversal with FVG context: 163 trades, +7.63 pts expectancy, PF 1.46.

The samples are sufficiently large to treat both relationships as supported diagnostics rather than tiny-cell artifacts.

## Interpretation

The reversal family should not be treated as homogeneous. Sweep/reversal context alone is not enough to explain edge; stronger downstream confirmation appears important.

This finding is consistent with [[F007-Short-Liquidity-Sweep-Weakness]] and suggests that the weak short-reversal bucket may partly reflect insufficient downstream confirmation rather than a general failure of liquidity sweeps.

## Limitation

The archived trade ledgers expose only compressed booleans for displacement, structure shift, and FVG context. They do not separately preserve MSS versus CHOCH, reclaim quality, FVG creation versus retest, or exact sequence timing.

EXP-007, EXP-009, EXP-010, and EXP-011 should isolate those components before any production filter or score-weight change is considered.
