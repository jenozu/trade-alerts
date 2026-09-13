# EXP-008 — Breakout / Acceptance Quality

Status: Complete — diagnostic only

Evidence:
- [[../../../research-archive/EXP-008/EXP-008-Breakout-Acceptance-Quality]]

## Objective

Determine which observable breakout/acceptance characteristics are associated with stronger continuation trades.

## Sample

- Total baseline trades: 1,218
- Continuation trades: 185
- Feature coverage: 185 / 185

## 1-minute close break

- No directional close break: 47 trades, +4.60 pts expectancy, PF 1.26.
- Directional close break: 138 trades, +6.38 pts, PF 1.37.

This is a modest aggregate improvement, but not cross-year monotonic:

- 2023 favored close-break confirmation.
- 2024 favored the no-close-break subset.
- 2025 also favored the no-close-break subset.

Therefore a mandatory 1m close requirement is not justified by EXP-008.

## Stored break confirmation

- Missing confirmation: 117 trades, +2.83 pts / PF 1.16.
- `body_close`: 17 trades, +29.13 / PF 3.29.
- `displacement`: 51 trades, +5.29 / PF 1.31.

The `body_close` subset is highly promising but sample-limited.

## Completed 5-minute close beyond level

- No completed 5m close: 163 trades, +4.68 pts / PF 1.27.
- Completed 5m close: 22 trades, +15.17 / PF 1.94.

The completed-5m subset was positive in all three years:

- 2023: +12.50 / PF 1.87, n=7.
- 2024: +16.42 / PF 1.98, n=6.
- 2025: +16.42 / PF 1.98, n=9.

This is promising but preliminary because the full sample is only 22 trades.

## Retest

No continuation trade in the archived baseline completed a qualifying retest before the existing signal.

Therefore EXP-008 cannot answer whether waiting for a retest improves expectancy.

That question requires an alternative-entry simulation that measures:
- setups lost by waiting;
- later entry price;
- altered MAE/MFE;
- false-break reduction.

Do not interpret the absence of retest trades as evidence against retests.

## Displacement category

- Missing: 117 trades, +2.83 / PF 1.16.
- Moderate: 11 trades, +46.45 / PF 6.06.
- Strong: 51 trades, +5.29 / PF 1.31.
- Weak: 6 trades, -2.62 / PF 0.86.

The moderate bucket is too small to promote, but weak displacement does not look encouraging.

## Break RVOL

Among the 68 trades with stored breakout RVOL:

- lowest quartile: -2.68 / PF 0.86.
- Q2: +19.60 / PF 2.26.
- Q3: +12.50 / PF 1.84.
- Q4: +15.57 / PF 2.05.

This suggests breakout volume may help distinguish continuation quality, but each quartile contains only 17 trades.

EXP-015 should examine RVOL formally across the broader sample.

## Limitations

- Existing trades only; no alternate entries were simulated.
- Retest opportunity cost cannot be measured here.
- Many detailed structure-break fields existed for only 68 / 185 continuations.
- Several high-performing cells contain fewer than 30 trades.
- Diagnostic association does not establish causal improvement.

## Decision

**INVESTIGATE — no strategy change.**

Do not:
- require 1m close confirmation;
- require a 5m close;
- require a retest;
- change breakout RVOL thresholds;
- alter continuation scoring.

The 5m-close and breakout-volume signals should remain later research candidates.
