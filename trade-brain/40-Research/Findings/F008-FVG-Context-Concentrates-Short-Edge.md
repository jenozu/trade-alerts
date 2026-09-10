# F008 — FVG context concentrates short edge

Status: Preliminary

Source: [[../Experiments/EXP-002-Long-vs-Short]]

## Finding

In the combined 2023–2025 baseline, short trades with `fvg_context=True` were strongly profitable while short trades without FVG context were slightly negative.

## Evidence

- SHORT with FVG context: 82 trades, +8.48 pts expectancy, PF 1.50.
- SHORT without FVG context: 483 trades, -0.91 pts expectancy, PF 0.95.
- LONG with FVG context: 93 trades, +7.40 pts expectancy, PF 1.45.
- LONG without FVG context: 560 trades, +2.19 pts expectancy, PF 1.13.

## Interpretation

FVG context is associated with materially stronger outcomes in both directions and appears particularly important for shorts because the short cohort changes from negative without FVG context to strongly positive with it.

## Limitation

This EXP-002 result is aggregate and does not establish year-by-year stability, FVG subtype, causal ordering, retest quality, or whether FVG is simply proxying displacement/structure. EXP-011 must test those questions before any weight change.
