# EXP-014 — Draw on Liquidity

Status: Complete — diagnostic only

Evidence:
- [[../../../research-archive/EXP-014/EXP-014-Draw-on-Liquidity]]

## Coverage

- Baseline trades: 1,218
- Exact feature coverage: 1,218 / 1,218

## Alignment

The historical baseline was already overwhelmingly DOL-aligned:

- aligned: 1,189 trades, +1.83 expectancy / PF 1.10
- neutral/unknown: 28 trades, +0.86 / PF 1.04
- opposed: 1 trade, -25.25 / PF 0.00

Therefore EXP-014 cannot honestly estimate the value of a hard DOL-alignment filter because the baseline selection process already excluded almost all opposed trades.

## Target category

Notable aggregate cells:

- equal highs/lows: +5.96 / PF 1.36, n=137
- ONH/ONL: +5.57 / PF 1.33, n=79
- weekly high/low: +2.32 / PF 1.13, n=249
- external swings: +0.16 / PF 1.01, n=552
- PDH/PDL: +0.24 / PF 1.01, n=126

Small LOH/LOL samples were strong but too thin for conclusions.

## Target-type asymmetry

Several high-side and low-side target types behaved very differently.

Examples:

- internal equal low: +14.22 / PF 1.91
- external equal high: +12.37 / PF 1.83
- PMH: +24.10 / PF 2.95, n=18
- PML: -16.76 / PF 0.27, n=22
- PDH: +7.45 / PF 1.52
- PDL: -6.12 / PF 0.69

These differences are interesting but partly overlap trade direction and year/regime effects.

## DOL confidence

Confidence was not monotonic:

- lowest quartile: +1.35 / PF 1.07
- second quartile: -1.91 / PF 0.90
- third quartile: +4.64 / PF 1.27
- highest quartile: +2.78 / PF 1.16

A simple minimum-confidence cutoff is not justified.

## Distance to target

Distance was also non-monotonic:

- ~25–37.75 pts: +2.47 / PF 1.14
- ~37.75–57.25: +1.28 / PF 1.07
- ~57.25–93.5: -0.16 / PF 0.99
- >93.5: +3.63 / PF 1.20

A simple "closer target is always better" rule is unsupported.

## Setup-family context

Continuation trades aligned with DOL:

- 180 trades
- +6.79 expectancy
- PF 1.40

Reversal trades aligned with DOL:

- 1,009 trades
- +0.94 expectancy
- PF 1.05

This largely reflects the setup-family asymmetry already documented in EXP-003.

## 2024 context

2024 external-swing targets were particularly weak:

- 173 trades
- -3.53 expectancy
- PF 0.82

Weekly-high/low targets were strong:

- 77 trades
- +9.90 expectancy
- PF 1.62

This suggests target destination may be part of regime behavior, but EXP-014 does not justify changing target selection yet.

## Decision

**INVESTIGATE — no strategy change.**

DOL currently appears more useful as:

1. directional/context information;
2. target-selection context;

than as a newly validated hard filter.

No DOL weight, target rule, entry rule, stop, or exit logic changed.
