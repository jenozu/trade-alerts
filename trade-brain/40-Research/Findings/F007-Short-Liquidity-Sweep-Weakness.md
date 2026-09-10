# F007 — Short liquidity-sweep weakness

Status: Preliminary

Source: [[../Experiments/EXP-002-Long-vs-Short]]

## Finding

In the combined 2023–2025 baseline, short trades carrying `liquidity_sweep=True` underperformed short trades without that flag by a large margin.

## Evidence

- Short + sweep present: 455 trades, -1.60 pts expectancy, PF 0.91.
- Short + sweep absent: 110 trades, +8.94 pts expectancy, PF 1.52.
- Longs did not show the same inversion: sweep-present longs were +3.12 pts expectancy / PF 1.18 and sweep-absent longs were +1.51 / PF 1.09.

## Interpretation

This is a meaningful diagnostic warning that the current sweep representation may not mean the same thing for shorts as it does for longs, or that short sweep setups require additional context before they deserve positive score contribution.

## Limitation

EXP-002 did not establish year-by-year stability for this exact sweep-conditioned split. Do not change sweep weights or apply a short-side filter from this result alone. EXP-007 should test sweep direction, reclaim quality, displacement, MSS/CHOCH, and FVG sequencing explicitly.
