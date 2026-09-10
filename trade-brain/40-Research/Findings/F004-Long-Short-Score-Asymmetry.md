# F004 — Long/short score asymmetry

Status: Supported

Source: [[../Experiments/EXP-001-Score-Band-Analysis]]

## Finding

The current score discriminates long setups materially better than short setups in the observed 2023–2025 baselines.

## Evidence

### 70–79
- Long: 509 trades, +1.67 pts expectancy, PF 1.10.
- Short: 449 trades, -0.14 pts expectancy, PF 0.99.

### 80–89
- Long: 131 trades, +7.52 pts expectancy, PF 1.43.
- Short: 108 trades, +1.04 pts expectancy, PF 1.05.

## Next validation

EXP-002 should decompose long vs short behavior before changing any scorer weights.
