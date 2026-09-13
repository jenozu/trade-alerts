# F026 — Displacement value is strongly setup-family dependent

Status: Supported

Sources:
- [[../Experiments/EXP-003-Setup-Family-Comparison]]
- [[../Experiments/EXP-007-Liquidity-Sweep-Contribution]]
- [[../Experiments/EXP-009-Displacement]]

## Finding

Directional displacement is much more informative for continuation trades than for reversal trades.

## Evidence

EXP-009:

Continuation:
- without directional displacement: +1.21 expectancy / PF 1.07;
- with directional displacement: +10.91 / PF 1.66.

Reversal:
- without directional displacement: +1.34 / PF 1.08;
- with directional displacement: +0.20 / PF 1.01.

EXP-007 separately showed that post-sweep displacement helped distinguish better sweep reversals, which is a different event-sequence question.

## Interpretation

Displacement should not be treated as one universal binary scoring input across both setup families.

Later score calibration should test family-specific contribution rather than simply increasing displacement weight globally.
