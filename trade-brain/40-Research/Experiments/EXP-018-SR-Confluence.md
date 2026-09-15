# EXP-018 — Support / Resistance Confluence

Status: Complete — diagnostic only

Evidence:
- [[../../../research-archive/EXP-018/EXP-018-SR-Confluence]]

## Coverage

- Baseline trades: 1,218
- Exact feature coverage: 1,218 / 1,218

## Persisted confluence alignment

Directional confluence alignment separated quality:

- aligned: 1,184 trades, +1.97 expectancy / PF 1.11
- not aligned: 34 trades, -4.56 / PF 0.78

The non-aligned sample is small, but clearly weaker.

## Confluence score

The numeric confluence score was not monotonic.

- roughly 23–53: +2.23 / PF 1.13
- roughly 53–93: -0.83 / PF 0.96

Score bands:

- <=30: -4.56 / PF 0.78
- 30–50: +20.41 / PF 2.89, but only 14 trades
- 50–60: +2.15 / PF 1.12
- 60–70: -2.82 / PF 0.86
- 70–80: +2.15 / PF 1.13
- 80–90: +14.50 / PF 1.96, only 5 trades
- 90+: -24.83 / PF 0.00, only 3 trades

Therefore higher confluence score is not automatically better.

## Equal-high / equal-low clusters

Total equal-cluster count:

- 0 clusters: +1.18 / PF 1.07
- 1 cluster: +3.04 / PF 1.18
- 2 clusters: -0.80 / PF 0.96
- 3+: only 1 trade

One nearby equal-liquidity cluster improved aggregate quality, but more clusters did not produce a monotonic improvement.

Notable cells:

- internal swing-low cluster present: +3.99 / PF 1.25
- external swing-low cluster present: +3.58 / PF 1.20
- external swing-high cluster present: +2.53 / PF 1.14
- internal swing-high cluster present: +1.39 / PF 1.08

## Setup-family interaction

Reversal:

- aligned: +1.21 / PF 1.07
- not aligned: -3.93 / PF 0.81

Continuation:

- aligned: +6.10 / PF 1.35
- not aligned: only 1 trade

The continuation result is consistent with prior evidence that continuation setups were stronger overall, but the non-aligned continuation sample is too small to estimate the independent confluence effect.

## Interpretation

EXP-018 supports confluence as useful context, but rejects the assumption that simply accumulating more confluence always improves trade quality.

The persisted score likely contains redundant or differently valuable components.

## Decision

**INVESTIGATE — no strategy change.**

Do not:

- increase score solely because more S/R elements overlap;
- require a high confluence score;
- treat every confluence source as equally valuable;
- create a hard filter yet.

Later calibration should focus on source quality and interaction rather than raw confluence count.
