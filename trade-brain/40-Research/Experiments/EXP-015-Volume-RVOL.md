# EXP-015 — Volume / RVOL

Status: Complete — diagnostic only

Evidence:
- [[../../../research-archive/EXP-015/EXP-015-Volume-RVOL]]

## Coverage

- Baseline trades: 1,218
- Exact feature coverage: 1,218 / 1,218

## Rolling RVOL

Rolling RVOL was useful but non-monotonic.

Quartiles:

- lowest: +0.08 expectancy / PF 1.00
- Q2: +3.00 / PF 1.17
- Q3: +1.83 / PF 1.10
- highest: +2.23 / PF 1.12

Threshold view:

- RVOL >=1.20: +2.19 / PF 1.12
- RVOL <1.20: +0.77 / PF 1.04
- RVOL >=1.50: +2.47 / PF 1.14
- RVOL <1.50: +0.83 / PF 1.05
- RVOL >=2.00: +1.44 / PF 1.08
- RVOL <2.00: +2.02 / PF 1.11

There is no evidence for a simple "more RVOL is always better" rule.

## Time-of-day RVOL

Time-of-day-normalized RVOL was especially non-linear.

Quartiles:

- Q1: +0.92 / PF 1.05
- Q2: +2.28 / PF 1.13
- Q3: +4.10 / PF 1.23
- Q4: -1.08 / PF 0.94

At the extreme:

- TOD RVOL >=2.00: -3.69 / PF 0.81
- TOD RVOL <2.00: +2.28 / PF 1.13

Extreme relative volume versus the time-of-day baseline appears harmful in aggregate.

## Volume percentile

Rolling volume percentile was also non-monotonic:

- 0–65: +0.34 / PF 1.02
- 65–85: +3.45 / PF 1.20
- 85–95: -2.33 / PF 0.88
- 95–100: +6.81 / PF 1.40

This makes a single percentile cutoff inappropriate.

## Structure-break RVOL

Structure-break RVOL showed strong separation:

- lowest quartile: -5.82 / PF 0.70
- Q2: +6.69 / PF 1.41
- Q3: +5.44 / PF 1.32
- Q4: +4.91 / PF 1.28

This is one of the stronger EXP-015 findings.

Low-volume structure breaks appear materially weaker than structure breaks occurring on stronger relative volume.

## Volume spikes

A generic volume spike was not particularly discriminating:

- no spike: +1.64 / PF 1.09
- spike: +1.83 / PF 1.10

Rolling-volume spikes showed somewhat better expectancy, but volume spike presence alone is not sufficient as a quality filter.

## Interpretation

Volume appears most useful when interpreted in context:

- breakout / structure event;
- time-of-day normalization;
- setup family;
- displacement.

Raw or generic "high volume" is too blunt.

## Decision

**INVESTIGATE — no strategy change.**

Do not:

- impose a universal minimum RVOL;
- require volume spikes;
- reject all extreme volume;
- change scoring weights yet.

Structure-event RVOL and moderate time-of-day-relative volume are the strongest candidates for later scoring/refinement tests.
