# F018 — HTF composite conflict is not a universal filter

Status: Supported

Source: [[../Experiments/EXP-006-HTF-Bias]]

## Finding

The production intraday HTF composite does not support treating component conflict as a universal no-trade condition in the already-selected 2023–2025 baseline.

## Evidence

Aggregate:
- aligned: 803 trades, +1.86 pts expectancy, PF 1.10.
- conflicting: 415 trades, +1.64 pts expectancy, PF 1.09.

By year:
- 2023 aligned +2.23 / PF 1.13; conflicting +3.90 / PF 1.23.
- 2024 aligned -0.81 / PF 0.96; conflicting +2.29 / PF 1.13.
- 2025 aligned +3.74 / PF 1.21; conflicting -1.00 / PF 0.95.

By setup family:
- continuation aligned +5.35 / PF 1.31; conflicting +7.81 / PF 1.47.
- reversal aligned +1.11 / PF 1.06; conflicting +0.93 / PF 1.05.

## Interpretation

The aggregate difference is small and the sign reverses by year. Conflict among HTF components behaves as interacting context rather than a stable standalone filter.

This does not mean HTF bias has no value. Individual timeframe relations, especially 1H and 15m, show more discrimination than the composite conflict flag.

## Implication

Do not convert HTF component conflict into a hard exclusion rule. Preserve it for later controlled ablation and interaction testing.
