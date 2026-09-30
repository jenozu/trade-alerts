# R4.6 — Score-Threshold Replay Statistical Review

## Status

Completed statistical review of the true chronological threshold replays for 2023, 2024 and 2025.

This phase changes **score eligibility threshold only**. It does not change production strategy settings, entry logic, stop logic, targets, time window, or setup-family rules.

The replay is path-dependent: a higher threshold can remove an earlier trade and therefore make a later signal executable. Results therefore come from full chronological re-simulation rather than filtering already executed trades.

Threshold 70 remains the frozen parity gate against the verified R4.5 trade ledgers.

## Research question

Does requiring a higher confluence score improve trade quality consistently enough across years to justify later validation?

Models reviewed:

- baseline
- candidate_conservative
- candidate_evidence_tilt
- candidate_redundancy_reduced

Thresholds reviewed:

- 70
- 75
- 80
- 85

## Baseline threshold result

The original baseline did **not** show stable monotonic improvement as the threshold increased.

2023 expectancy by threshold:

- 70: +2.9157
- 75: +3.7104
- 80: +4.7336
- 85: +19.1033

2024 expectancy by threshold:

- 70: +0.1707
- 75: -1.3529
- 80: -3.1983
- 85: -0.5057

2025 expectancy by threshold:

- 70: +2.2701
- 75: +4.7442
- 80: +7.4274
- 85: +20.1196

The high baseline threshold therefore looked strong in pooled terms but remained materially regime-dependent. Raising the threshold did not solve the weak 2024 behavior.

## Candidate Conservative

The conservative candidate remained negative in 2024 at every tested threshold:

- 70: -1.7571 expectancy
- 75: -1.7607
- 80: -1.6673
- 85: -2.0962

The strong 2025 threshold-85 result did not generalize across years.

Current disposition: **deprioritize for threshold calibration**.

## Candidate Evidence Tilt

Threshold 80 produced positive expectancy in every research year while retaining substantially more trades than threshold 85:

| Year | Trades | Expectancy | PF | Net points | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2023 | 166 | +6.4036 | 1.3899 | +1063.00 | 296.25 |
| 2024 | 172 | +1.3343 | 1.0753 | +229.50 | 537.25 |
| 2025 | 221 | +5.1561 | 1.2830 | +1139.50 | 478.50 |

Combined:

- 559 trades
- +2432.00 net points
- +4.3506 points/trade

Threshold 85 also remained positive in all three years, but the sample fell to 263 trades and 2023 expectancy was lower than threshold 80.

This suggests a useful quality transition near 80, but not a perfectly monotonic score.

Current disposition: **promising candidate for later out-of-sample validation; no production change**.

## Candidate Redundancy Reduced

The redundancy-reduced model was weak at threshold 70 but became materially stronger at threshold 85:

| Year | Trades | Expectancy | PF | Net points | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2023 | 92 | +4.1576 | 1.2457 | +382.50 | 212.75 |
| 2024 | 85 | +4.1265 | 1.2370 | +350.75 | 359.50 |
| 2025 | 106 | +12.8750 | 1.7617 | +1364.75 | 178.00 |

Combined:

- 283 trades
- +2098.00 net points
- +7.4134 points/trade

This is encouraging because 2024 remained profitable rather than being carried entirely by 2023/2025.

The sample is materially smaller, so the result remains exploratory.

Current disposition: **promising high-score candidate for later out-of-sample validation; no production change**.

## Main conclusions

1. Raising the original baseline threshold is not sufficient. The baseline score remains regime-sensitive.
2. Candidate Evidence Tilt around threshold 80 is the best current balance of cross-year consistency and sample size.
3. Candidate Redundancy Reduced at threshold 85 is a strong high-selectivity candidate, but has a much smaller sample.
4. Candidate Conservative does not solve the 2024 weakness.
5. Higher threshold is not automatically better. Score quality is not perfectly monotonic.
6. These results do not authorize production changes because the candidate score configurations and thresholds were evaluated retrospectively on the same research universe.

## Decision

**INVESTIGATE — NO PRODUCTION CHANGE.**

R4.6 supports carrying Evidence Tilt 80 and Redundancy Reduced 85 forward as validation candidates.

They must not be combined with unrelated stop, target, entry, or setup-rule changes inside the same isolated experiment.

## Next strategy-refinement work

The roadmap already contains Phase R6 — Exit / trade-management experiments.

The next target-specific test will therefore be added **inside the existing R6 family**, not as a competing or redundant experiment.

The first exit experiment will isolate the full-position target distance while preserving:

- baseline scoring;
- threshold 70;
- current setup eligibility;
- current entry logic;
- current stop logic;
- current session/time rules;
- one-position-at-a-time behavior;
- slippage assumptions.

Full targets to compare:

- 50 points
- 75 points
- 100 points (frozen control)

The 100-point run must reproduce the frozen baseline before the exploratory 50/75-point runs are accepted.
