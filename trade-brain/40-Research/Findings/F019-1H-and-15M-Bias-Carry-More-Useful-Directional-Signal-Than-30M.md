# F019 — 1H and 15m bias carry more useful directional signal than 30m in the baseline

Status: Supported

Source: [[../Experiments/EXP-006-HTF-Bias]]

## Finding

Within the already-selected baseline trades, individual HTF relations are not equally informative. The 1H and 15m directional relations show positive discrimination, while the 30m relation moves in the opposite direction.

## Evidence

Aligned-minus-known-non-aligned expectancy lift:
- 1H: +5.18 pts/trade.
- 15m: +2.52.
- 4H: +1.94.
- 1D: +1.14.
- 30m: -5.56.

Key cells:
- 1H aligned: 1,169 trades, +1.99 expectancy, PF 1.11.
- 1H opposed: 49 trades, -3.18, PF 0.84.
- 15m aligned: 917 trades, +2.41, PF 1.14.
- 15m opposed: 301 trades, -0.12, PF 0.99.
- 30m aligned: 1,103 trades, +1.26, PF 1.07.
- 30m opposed: 115 trades, +6.82, PF 1.42.

Pairwise state agreement was 86.5% between 1H and 30m, 74.1% between 30m and 15m, and 71.3% between 1H and 15m.

## Interpretation

The current equal conceptual treatment of HTF inputs deserves later ablation. The 30m result should not be interpreted as evidence to invert 30m bias because this is observational and selection-conditioned.

## Implication

Prioritize controlled 1H/30m/15m ablation during score-component calibration. Test whether 30m is redundant or harmful only after removing the current selection effect.
