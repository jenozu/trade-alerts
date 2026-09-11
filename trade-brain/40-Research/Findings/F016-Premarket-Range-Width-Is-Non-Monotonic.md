# F016 — Premarket range width is non-monotonic

Status: Supported

Source: [[../Experiments/EXP-005-Important-Liquidity-Level]]

## Finding

Premarket high-to-low range width materially separates historical performance, but the relationship is non-monotonic. The data does not support a simple rule that wider or narrower premarket ranges are always better.

## Evidence

EXP-005 quartiles across the 1,218-trade baseline:

- Q1 narrow, 13.75–82.50 pts: 312 trades, -0.04 expectancy, PF 1.00, -13.50 net points.
- Q2, 82.75–114.75 pts: 297 trades, +7.63 expectancy, PF 1.47, +2,266.75 net points.
- Q3, 115.25–157.00 pts: 306 trades, -4.10 expectancy, PF 0.79, -1,253.25 net points.
- Q4 wide, 157.75–839.25 pts: 303 trades, +3.87 expectancy, PF 1.21, +1,172.50 net points.

## Interpretation

Range width appears to interact with other market conditions rather than acting as a standalone linear quality measure. Q2 and Q4 were profitable while Q1 was flat and Q3 was materially negative.

## Implication

Do not introduce a simple maximum/minimum PMH–PML width filter from EXP-005. This feature should be revisited in the later regime/day-type and interaction research, with year, setup family, direction, SNR/RVOL, and confirmation context controlled.
