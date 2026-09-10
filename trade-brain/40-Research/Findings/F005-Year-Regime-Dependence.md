# F005 — Year/regime dependence

Status: Supported

Sources:
- [[../Experiments/EXP-001-Score-Band-Analysis]]
- [[../Experiments/EXP-002-Long-vs-Short]]
- [[../Experiments/EXP-003-Setup-Family-Comparison]]

## Finding

Directional, score-band, and setup-family behavior varies materially across years, so aggregate results should not be treated as a universal relationship between score, direction, setup family, and outcome.

## Evidence

EXP-001 showed materially different year-by-year behavior within the same score bands.

EXP-002 added clear directional regime dependence:

- 2023 LONG: 181 trades, +2.33 pts expectancy, PF 1.14.
- 2023 SHORT: 163 trades, +3.56 pts expectancy, PF 1.21.
- 2024 LONG: 221 trades, +1.50 pts expectancy, PF 1.09.
- 2024 SHORT: 167 trades, -1.59 pts expectancy, PF 0.91.
- 2025 LONG: 251 trades, +4.63 pts expectancy, PF 1.26.
- 2025 SHORT: 235 trades, -0.25 pts expectancy, PF 0.99.

The long-minus-short performance gap therefore reverses sign in 2023 relative to 2024–2025.

EXP-003 adds setup-family decomposition and explains much of the weak 2024 aggregate:

- 2023 reversal: 298 trades, +2.79 pts expectancy, PF 1.17.
- 2023 continuation: 46 trades, +3.76 pts expectancy, PF 1.22.
- 2024 reversal: 328 trades, -1.61 pts expectancy, PF 0.91, -526.50 net points.
- 2024 continuation: 60 trades, +9.88 pts expectancy, PF 1.63, +592.75 net points.
- 2025 reversal: 407 trades, +1.90 pts expectancy, PF 1.10.
- 2025 continuation: 79 trades, +4.18 pts expectancy, PF 1.22.

Continuation outperformed reversal in all three years, but the magnitude of the gap varied substantially, with 2024 showing the strongest divergence.

## Implication

The aggregate long advantage is meaningful but not sufficiently stable to justify a production long/short split. EXP-003 also shows that the weak 2024 baseline was not broad strategy failure: weakness was concentrated in the reversal-classified majority while the continuation bucket remained strongly profitable.

Future scorer calibration and strategy refinements must be checked across individual years/regimes and setup families, then validated out-of-sample rather than optimized on the combined sample alone.

EXP-004 remains the dedicated year/regime decomposition experiment.
