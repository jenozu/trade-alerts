# F005 — Year/regime dependence

Status: Supported

Sources:
- [[../Experiments/EXP-001-Score-Band-Analysis]]
- [[../Experiments/EXP-002-Long-vs-Short]]
- [[../Experiments/EXP-003-Setup-Family-Comparison]]
- [[../Experiments/EXP-004-Year-and-Regime-Stability]]
- [[../Experiments/EXP-005-Important-Liquidity-Level]]
- [[../Experiments/EXP-006-HTF-Bias]]

## Finding

Directional, score-band, setup-family, level-specific, and HTF-context behavior varies materially across years, so aggregate results should not be treated as a universal relationship between context and outcome.

## Evidence

EXP-002 established directional regime dependence:

- 2023 LONG: +2.33 pts expectancy, PF 1.14; SHORT: +3.56, PF 1.21.
- 2024 LONG: +1.50, PF 1.09; SHORT: -1.59, PF 0.91.
- 2025 LONG: +4.63, PF 1.26; SHORT: -0.25, PF 0.99.

EXP-003 established setup-family dependence:

- 2023 reversal +2.79 / PF 1.17; continuation +3.76 / PF 1.22.
- 2024 reversal -1.61 / PF 0.91; continuation +9.88 / PF 1.63.
- 2025 reversal +1.90 / PF 1.10; continuation +4.18 / PF 1.22.

EXP-004 added score-band/context decomposition:

- 70–79: 2023 +3.62 / PF 1.22; 2024 -0.24 / PF 0.99; 2025 -0.28 / PF 0.99.
- 80–89: 2023 -0.67 / PF 0.96; 2024 +3.41 / PF 1.18; 2025 +10.00 / PF 1.57.

EXP-005 shows level identity is also regime-dependent:

- PMH/PML: 2023 -8.06, 2024 +2.90, 2025 -4.95 pts expectancy.
- Internal swing: 2023 +5.93, 2024 -2.14, 2025 +5.01.
- External swing: 2023 +6.91, 2024 -1.40, 2025 +2.24.
- Overnight high/low: 2023 -5.48, 2024 +6.08, 2025 +6.00.

EXP-006 strengthens the regime-dependence warning for HTF context:

- 2023 headline HTF aligned +2.23 / PF 1.13; conflicting +3.90 / PF 1.23.
- 2024 aligned -0.81 / PF 0.96; conflicting +2.29 / PF 1.13.
- 2025 aligned +3.74 / PF 1.21; conflicting -1.00 / PF 0.95.

## Interpretation

2024 was not a broad failure of every component. Weakness was concentrated in reversal-classified trades, shorts, the dominant 70–79 score band, and several swing-level groups that were profitable in 2023/2025. Continuations, displacement-present trades, FVG-context trades, and some session-level groups remained profitable.

EXP-006 shows that even the meaning of HTF component agreement changes by year: conflict outperformed alignment in 2023–2024, while alignment was clearly stronger in 2025. HTF context should therefore be treated as interacting context rather than a universally stable standalone filter.

## Implication

No aggregate long/short, score-band, setup-family, level-specific, or HTF-context result should be promoted directly into production rules without year/regime checks and later out-of-sample validation. Component experiments should explicitly report cross-year stability rather than only combined-sample lift.
