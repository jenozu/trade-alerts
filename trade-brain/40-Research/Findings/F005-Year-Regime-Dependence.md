# F005 — Year/regime dependence

Status: Supported

Sources:
- [[../Experiments/EXP-001-Score-Band-Analysis]]
- [[../Experiments/EXP-002-Long-vs-Short]]

## Finding

Directional and score-band behavior varies materially across years, so aggregate results should not be treated as a universal relationship between score, direction, and outcome.

## Evidence

EXP-001 showed materially different year-by-year behavior within the same score bands.

EXP-002 adds a clear direction example:

- 2023 LONG: 181 trades, +2.33 pts expectancy, PF 1.14.
- 2023 SHORT: 163 trades, +3.56 pts expectancy, PF 1.21.
- 2024 LONG: 221 trades, +1.50 pts expectancy, PF 1.09.
- 2024 SHORT: 167 trades, -1.59 pts expectancy, PF 0.91.
- 2025 LONG: 251 trades, +4.63 pts expectancy, PF 1.26.
- 2025 SHORT: 235 trades, -0.25 pts expectancy, PF 0.99.

The long-minus-short performance gap therefore reverses sign in 2023 relative to 2024–2025.

## Implication

The aggregate long advantage is meaningful but not sufficiently stable to justify a production long/short split. Future scorer calibration and strategy refinements must be checked across individual years/regimes and then validated out-of-sample rather than optimized on the combined sample alone.

EXP-004 remains the dedicated year/regime decomposition experiment.
