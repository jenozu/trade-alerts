# F025 — Baseline continuations did not wait for a completed retest

Status: Supported

Sources:
- [[../Experiments/EXP-008-Breakout-Acceptance-Quality]]

## Finding

None of the 185 archived continuation trades contained a qualifying post-break retest before the existing signal.

## Interpretation

The current baseline does not provide an observational with-retest versus without-retest comparison.

Whether waiting for a retest would improve quality requires explicit alternative-entry simulation that accounts for missed trades and worse/better entry prices.

EXP-008 therefore makes no claim that retests help or hurt performance.
