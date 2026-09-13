# EXP-009 — Displacement

Status: Complete — diagnostic only

Evidence:
- [[../../../research-archive/EXP-009/EXP-009-Displacement]]

## Objective

Determine whether displacement contributes meaningful trade-quality information and whether its value differs by setup family, direction, year, and accompanying structure context.

## Aggregate directional displacement

- No directional displacement: 859 trades, +1.32 pts expectancy, PF 1.07.
- Directional displacement: 359 trades, +2.88 pts, PF 1.16.

Directional displacement improved aggregate expectancy, but the effect was not stable across all years.

## Year stability

2023:
- absent: +4.13 / PF 1.26
- present: +0.00 / PF 1.00

2024:
- absent: -1.28 / PF 0.93
- present: +3.45 / PF 1.19

2025:
- absent: +1.38 / PF 1.07
- present: +4.50 / PF 1.25

Therefore displacement is regime-dependent rather than universally beneficial.

## Direction

LONG:
- absent: +1.85 / PF 1.11
- present: +6.22 / PF 1.37

SHORT:
- absent: +0.62 / PF 1.03
- present: +0.14 / PF 1.01

The aggregate displacement lift is concentrated heavily on the long side.

## Setup family

REVERSAL:
- absent: +1.34 / PF 1.08
- present: +0.20 / PF 1.01

CONTINUATION:
- absent: +1.21 / PF 1.07
- present: +10.91 / PF 1.66

This is the strongest EXP-009 result. Displacement appears much more informative for continuation quality than for reversal quality.

## Displacement category

- None: +6.39 / PF 1.36
- Weak: -0.58 / PF 0.97
- Moderate: -1.44 / PF 0.92
- Strong: +3.91 / PF 1.22

These labels are not monotonic enough to justify a simple category threshold.

## Displacement score

Observed directional-displacement quartiles:

- approximately 48.5–70.1: +0.18 / PF 1.01
- 70.1–82.7: -0.11 / PF 0.99
- 82.7–89.6: +5.69 / PF 1.32
- 89.6–100: +5.80 / PF 1.32

Higher displacement scores appear more useful than lower ones, but this remains diagnostic.

## Structure interaction

Across all trades:

- Same-direction structure break present: +3.99 / PF 1.23 versus +0.15 / PF 1.01 absent.
- Same-direction MSS present: +2.28 / PF 1.13 versus +1.70 / PF 1.10 absent.
- Same-direction CHOCH produced the same segmentation as MSS.
- Same-direction BOS present: +11.57 / PF 1.74 across 83 trades versus +1.07 / PF 1.06 absent.
- Same-direction FVG creation: +4.82 / PF 1.28 versus +0.95 / PF 1.05 absent.

The BOS result is particularly interesting but requires dedicated structure analysis in EXP-010.

## Limitations

- Existing baseline trades only.
- No alternate displacement threshold was simulated.
- Correlated structure/FVG inputs may explain part of displacement's apparent lift.
- MSS and CHOCH again produced identical segmentation and require direct redundancy testing.
- Observational results do not justify changing weights yet.

## Decision

**INVESTIGATE — no strategy change.**

Do not:
- increase displacement weight yet;
- require displacement for all setups;
- require a displacement-score threshold;
- alter reversal or continuation rules.

The strongest hypothesis carried into later refinement is that displacement matters substantially more for continuation setups than reversal setups.
