# F005 — Year/regime dependence

Status: Supported

Sources:
- [[../Experiments/EXP-001-Score-Band-Analysis]]
- [[../Experiments/EXP-002-Long-vs-Short]]
- [[../Experiments/EXP-003-Setup-Family-Comparison]]
- [[../Experiments/EXP-004-Year-and-Regime-Stability]]

## Finding

Directional, score-band, and setup-family behavior varies materially across years, so aggregate results should not be treated as a universal relationship between score, direction, setup family, and outcome.

## Evidence

EXP-002 established directional regime dependence:

- 2023 LONG: +2.33 pts expectancy, PF 1.14; SHORT: +3.56, PF 1.21.
- 2024 LONG: +1.50, PF 1.09; SHORT: -1.59, PF 0.91.
- 2025 LONG: +4.63, PF 1.26; SHORT: -0.25, PF 0.99.

EXP-003 established setup-family dependence:

- 2023 reversal +2.79 / PF 1.17; continuation +3.76 / PF 1.22.
- 2024 reversal -1.61 / PF 0.91; continuation +9.88 / PF 1.63.
- 2025 reversal +1.90 / PF 1.10; continuation +4.18 / PF 1.22.

EXP-004 adds score-band and context decomposition:

- 70–79: 2023 +3.62 / PF 1.22; 2024 -0.24 / PF 0.99; 2025 -0.28 / PF 0.99.
- 80–89: 2023 -0.67 / PF 0.96; 2024 +3.41 / PF 1.18; 2025 +10.00 / PF 1.57.
- HTF-aligned trades stayed positive in all three years, but 2024 was much weaker at +0.53 / PF 1.03 versus +2.95 / PF 1.18 in 2023 and +2.89 / PF 1.16 in 2025.
- Structure-shift behavior was not uniformly stable: structure-shift-absent trades were strong in 2023 but materially weak in 2024 and 2025.

## Interpretation

2024 was not a broad failure of every component. The largest weakness was concentrated in reversal-classified trades, shorts, and the dominant 70–79 score band. Continuations, displacement-present trades, and FVG-context trades remained profitable.

## Implication

No aggregate long/short, score-band, or setup-family result should be promoted directly into production rules without year/regime checks and later out-of-sample validation. Component experiments should explicitly report cross-year stability rather than only combined-sample lift.
