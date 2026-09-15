# EXP-019 — Room to Target

Status: Complete — diagnostic only

Evidence:
- [[../../../research-archive/EXP-019/EXP-019-Room-to-Target]]

## Coverage

- Baseline trades: 1,218
- Exact feature coverage: 1,218 / 1,218

## Primary DOL target distance

Performance was not monotonic.

- 25–49 pts: +2.48 expectancy / PF 1.14
- 50–74 pts: -0.89 / PF 0.95
- 75–99 pts: -0.22 / PF 0.99
- 100+ pts: +4.56 / PF 1.26

The widest-room group was strong, but the middle ranges were weak.

## Nearest unswept liquidity

The same non-linear pattern appeared:

- <25 pts: +18.18 / PF 2.20, but only 15 trades
- 25–49 pts: +1.67 / PF 1.10
- 50–74 pts: -1.73 / PF 0.91
- 75–99 pts: -1.79 / PF 0.91
- 100+ pts: +5.77 / PF 1.33

The <25-point sample is too small to justify a rule.

## Persisted room score

The historical room-to-target score had no useful variation in the surviving baseline trades; all trades occupied the same observed score quartile.

Therefore EXP-019 cannot validate that stored score as an independent ranking variable from this selected baseline alone.

## Major-obstacle flag

Only 15 trades carried the persisted major-obstacle flag:

- no obstacle: +1.58 / PF 1.09
- obstacle: +18.18 / PF 2.20

This is selection-confounded and sample-limited and does not imply obstacles are beneficial.

## Interpretation

Room to target matters, but not as a simple linear "more room is always better" rule.

The 50–99 point ranges were the weakest in this baseline, while 100+ point targets were materially stronger.

Target type and setup context likely interact with distance.

## Decision

**INVESTIGATE — no strategy change.**

Do not:

- impose a universal minimum room threshold;
- automatically reward every larger target distance;
- remove trades solely because a persisted obstacle flag exists.

Later refinement should test room jointly with target type, setup family, and expected capture.
