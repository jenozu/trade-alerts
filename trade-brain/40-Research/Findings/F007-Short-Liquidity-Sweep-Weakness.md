# F007 — Short liquidity-sweep weakness

Status: Supported

Sources:
- [[../Experiments/EXP-002-Long-vs-Short]]
- [[../Experiments/EXP-003-Setup-Family-Comparison]]

## Finding

In the combined 2023–2025 baseline, short trades carrying `liquidity_sweep=True` materially underperform short trades without that flag. EXP-003 strengthens this by showing the same split as a setup-family asymmetry under the production planner family-selection contract: short reversals are weak while short continuations are strong.

## Evidence

EXP-002:

- Short + sweep present: 455 trades, -1.60 pts expectancy, PF 0.91.
- Short + sweep absent: 110 trades, +8.94 pts expectancy, PF 1.52.
- Longs did not show the same inversion: sweep-present longs were +3.12 pts expectancy / PF 1.18 and sweep-absent longs were +1.51 / PF 1.09.

EXP-003 uses the deterministic archived-ledger projection of the planner family-selection rule:

- `liquidity_sweep=True` → reversal.
- `liquidity_sweep=False` → continuation.

The direction-within-family results were therefore:

- SHORT reversal: 455 trades, -1.60 pts expectancy, -0.064R, PF 0.91, -728.25 net points.
- SHORT continuation: 110 trades, +8.94 pts expectancy, +0.356R, PF 1.52, +983.25 net points.
- LONG reversal: 578 trades, +3.12 pts expectancy, PF 1.18.
- LONG continuation: 75 trades, +1.51 pts expectancy, PF 1.09.

The weakness is not a generic property of reversal classification: long reversals remained profitable.

## Interpretation

This is now supported as a real diagnostic asymmetry in the archived baseline. It does **not** prove that liquidity sweeps themselves should be removed or penalized for shorts. The more plausible research question is whether short reversal setups require stronger downstream confirmation or whether the current shared scorer overvalues the sweep/reversal context on the short side.

## Limitation

The archived trade ledger does not separately persist reclaim quality, MSS versus CHOCH, acceptance, or the full production setup-state sequence. EXP-003 therefore cannot identify the causal mechanism behind the short reversal weakness.

Do not change sweep weights or apply a production short-side filter from this finding alone. EXP-007 should test sweep direction, reclaim quality, displacement, MSS/CHOCH, and FVG sequencing explicitly.
