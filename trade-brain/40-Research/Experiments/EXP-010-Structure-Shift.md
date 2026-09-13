# EXP-010 — MSS / BOS / CHOCH / Structure Shift

Status: Complete — diagnostic only

Evidence:
- [[../../../research-archive/EXP-010/EXP-010-Structure-Shift]]

## Objective

Determine the contribution and redundancy of MSS, BOS, CHOCH, and structure-shift context.

## Coverage

- Baseline trades: 1,218
- Exact feature coverage: 1,218 / 1,218

## Recent MSS / CHOCH

Recent MSS:

- absent: 732 trades, +0.10 pts expectancy, PF 1.01
- present: 486 trades, +4.33 pts, PF 1.25

Recent CHOCH produced the exact same segmentation and metrics.

This strongly suggests MSS and CHOCH are redundant or equivalently encoded in the existing historical feature set.

They must not be treated as independent evidence without further implementation review.

## Recent BOS

- absent: 840 trades, +1.44 pts expectancy, PF 1.08
- present: 378 trades, +2.55 pts, PF 1.14

The aggregate BOS lift is modest.

## Any recent structure confirmation

- absent: 380 trades, -1.33 pts expectancy, PF 0.93
- present: 838 trades, +3.20 pts, PF 1.18

This is one of the stronger broad findings from EXP-010.

## Number of structure confirmations

- 0 confirmations: -1.33 / PF 0.93
- 1 confirmation: +1.63 / PF 1.09
- 2 confirmations: +3.72 / PF 1.21
- 3 confirmations: +15.01 / PF 1.93, n=26

The relationship is directionally encouraging but the 3-confirmation sample is small.

## Current same-direction structure break

- absent: +0.15 / PF 1.01
- present: +3.99 / PF 1.23

## Reversal structure behavior

MSS/CHOCH:

- absent: -0.96 / PF 0.95
- present: +3.70 / PF 1.21

BOS:

- absent: +1.26 / PF 1.07
- present: +0.29 / PF 1.02

For reversals, MSS/CHOCH appears much more useful than BOS.

## Continuation structure behavior

MSS/CHOCH:

- absent: +4.46 / PF 1.25
- present: +10.93 / PF 1.67, n=42

BOS:

- absent: +5.47 / PF 1.31
- present: +6.04 / PF 1.35

BOS is common in continuations but adds much less incremental separation than the earlier unconditional BOS result suggested.

## Sequence diagnostics

Sweep + displacement:

- absent: +0.16 / PF 1.01
- present: +2.85 / PF 1.16

Sweep + displacement + MSS/CHOCH:

- absent: +0.22 / PF 1.01
- present: +5.70 / PF 1.33

Continuation + displacement + BOS:

- absent: +1.21 / PF 1.07
- present: +6.70 / PF 1.39

These sequence results support the idea that combinations of structural confirmation matter more than isolated labels.

## Interpretation

Structure confirmation clearly contains useful information, but the current implementation likely contains correlated or duplicate representations.

MSS and CHOCH should not both receive independent scoring credit unless their implementation is later shown to encode genuinely different events.

## Limitations

- Existing baseline trades only.
- No delayed-entry simulation.
- No measurement of entry-price cost from waiting for structure confirmation.
- MSS and CHOCH appear identical in the historical feature artifacts.
- Correlated displacement and setup-family effects remain present.

## Decision

**INVESTIGATE — no strategy change.**

Do not:
- add a mandatory structure rule;
- increase MSS/CHOCH weight;
- double-count MSS and CHOCH;
- increase BOS weight globally.

The strongest later scoring candidate is setup-family-specific structure logic.
