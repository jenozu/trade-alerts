# F007 — Short liquidity-sweep weakness

Status: Supported

Sources:
- [[../Experiments/EXP-002-Long-vs-Short]]
- [[../Experiments/EXP-003-Setup-Family-Comparison]]
- [[../Experiments/EXP-005-Important-Liquidity-Level]]

## Finding

In the combined 2023–2025 baseline, short trades carrying `liquidity_sweep=True` materially underperform short trades without that flag. EXP-003 strengthened this through setup-family decomposition, and EXP-005 adds level-source evidence showing a large internal-swing high versus low asymmetry.

## Evidence

EXP-002:

- Short + sweep present: 455 trades, -1.60 pts expectancy, PF 0.91.
- Short + sweep absent: 110 trades, +8.94 pts expectancy, PF 1.52.
- Longs did not show the same inversion: sweep-present longs were +3.12 pts expectancy / PF 1.18 and sweep-absent longs were +1.51 / PF 1.09.

EXP-003:

- SHORT reversal: 455 trades, -1.60 pts expectancy, -0.064R, PF 0.91, -728.25 net points.
- SHORT continuation: 110 trades, +8.94 pts expectancy, +0.356R, PF 1.52, +983.25 net points.
- LONG reversal: 578 trades, +3.12 pts expectancy, PF 1.18.
- LONG continuation: 75 trades, +1.51 pts expectancy, PF 1.09.

EXP-005 exact source decomposition:

- `active_internal_swing_high`: 276 trades, -2.11 pts expectancy, -0.084R, PF 0.89, -581.00 net points.
- `active_internal_swing_low`: 296 trades, +7.56 pts expectancy, +0.301R, PF 1.46, +2,236.75 net points.
- Internal-swing shorts overall were essentially flat at -0.01 pts expectancy / PF 1.00, while the directional source split was much larger.

The exact-source result is consistent with the previously observed weakness in short-side reversal/sweep contexts, though it still does not establish the causal mechanism.

## Interpretation

This is supported as a real diagnostic asymmetry in the archived baseline. It does **not** prove that liquidity sweeps themselves should be removed or penalized for shorts. The more plausible research question is whether short reversal setups require stronger downstream confirmation, whether some swept level classes are inferior, or whether the current shared scorer overvalues the sweep/reversal context on the short side.

## Limitation

The archived trade ledger does not separately persist reclaim quality, MSS versus CHOCH, acceptance, or the full production setup-state sequence. EXP-005 also classifies level source rather than isolating causal sweep mechanics.

Do not change sweep weights or apply a production short-side filter from this finding alone. EXP-007 should test sweep direction, reclaim quality, displacement, MSS/CHOCH, and FVG sequencing explicitly.
