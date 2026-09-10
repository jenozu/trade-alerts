# F004 — Long/short score asymmetry

Status: Supported

Sources:
- [[../Experiments/EXP-001-Score-Band-Analysis]]
- [[../Experiments/EXP-002-Long-vs-Short]]

## Finding

The current score discriminates long setups materially better than short setups in the combined 2023–2025 baseline, especially in the two large observed score bands. EXP-002 strengthens the aggregate asymmetry found in EXP-001, but also shows that the long advantage is not stable in sign across every year.

## Evidence

### Overall
- LONG: 653 trades, +2.94 pts expectancy, PF 1.17, +1917.50 net points.
- SHORT: 565 trades, +0.45 pts expectancy, PF 1.02, +255.00 net points.
- Long-minus-short expectancy gap: +2.49 pts/trade.

### 70–79
- Long: 509 trades, +1.67 pts expectancy, PF 1.10.
- Short: 449 trades, -0.14 pts expectancy, PF 0.99.

### 80–89
- Long: 131 trades, +7.52 pts expectancy, PF 1.43.
- Short: 108 trades, +1.04 pts expectancy, PF 1.05.

### Score distribution
- LONG mean 76.11 / median 74.42.
- SHORT mean 75.36 / median 73.59.

The score distributions are close even though realized expectancy differs substantially.

### Year stability
- 2023: LONG +2.33 / PF 1.14; SHORT +3.56 / PF 1.21.
- 2024: LONG +1.50 / PF 1.09; SHORT -1.59 / PF 0.91.
- 2025: LONG +4.63 / PF 1.26; SHORT -0.25 / PF 0.99.

## Interpretation

The aggregate evidence supports directional calibration asymmetry, not a universal claim that longs are always better. The same score number currently maps to stronger realized performance for longs in the large 70–79 and 80–89 cohorts, but 2023 demonstrates that the effect is regime/year dependent.

## Decision relevance

Separate long/short scoring is now a justified **research candidate** for the later score-calibration phase, but there is not enough stability to split production configs or weights yet.

Related: [[F009-Similar-Scores-Different-Directional-Quality]] and [[F005-Year-Regime-Dependence]].
