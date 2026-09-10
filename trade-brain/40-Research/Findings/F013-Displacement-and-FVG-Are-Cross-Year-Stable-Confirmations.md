# F013 — Displacement and FVG are cross-year stable confirmations

Status: Supported

Source: [[../Experiments/EXP-004-Year-and-Regime-Stability]]

## Finding

Across the untouched 2023–2025 baseline, trades with directional displacement and trades with FVG context remained profitable in every year. Displacement-absent trades were negative in all three years.

## Evidence

Displacement present:

- 2023: 254 trades, +4.07 pts expectancy, PF 1.24.
- 2024: 290 trades, +2.41 pts expectancy, PF 1.14.
- 2025: 346 trades, +3.58 pts expectancy, PF 1.19.

Displacement absent:

- 2023: 90 trades, -0.34 pts expectancy, PF 0.98.
- 2024: 98 trades, -6.46 pts expectancy, PF 0.67.
- 2025: 140 trades, -0.97 pts expectancy, PF 0.95.

FVG context present:

- 2023: 51 trades, +11.21 pts expectancy, PF 1.71.
- 2024: 54 trades, +6.56 pts expectancy, PF 1.40.
- 2025: 70 trades, +6.54 pts expectancy, PF 1.37.

FVG context absent:

- 2023: +1.47 pts expectancy, PF 1.09.
- 2024: -0.86 pts expectancy, PF 0.95.
- 2025: +1.55 pts expectancy, PF 1.08.

## Interpretation

These are among the most cross-year-stable confirmation signals observed so far. This does not yet prove causal incremental value because the features may co-occur with other strong conditions.

## Implication

EXP-009 and EXP-011 should explicitly test the independent lift and redundancy of displacement and FVG before any scoring weight changes are made.
