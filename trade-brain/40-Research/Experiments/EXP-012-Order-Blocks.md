# EXP-012 — Order Blocks

Status: BLOCKED — not testable from current archived baseline artifacts

## Objective

Evaluate whether Order Block context contributes measurable edge to the strategy.

Planned comparisons included:

- OB present vs absent;
- OB retest vs no retest;
- OB + FVG overlap;
- sweep-reversal context;
- continuation context.

## Artifact capability audit

The verified 2023, 2024, and 2025 scored feature artifacts were inspected for Order Block-related fields.

Artifacts checked:

- 2023 `nq_1m_scored.parquet`
- 2024 `nq_1m_scored.parquet`
- 2025 `2025_warmup_92d/features_scored.parquet`

No actual Order Block fields were found.

The only keyword matches were:

- `long_score_penalty_major_obstacle`
- `short_score_penalty_major_obstacle`

These are false-positive text matches caused by `_ob_` appearing inside the word `obstacle`. They do not represent Order Block state, location, retest, mitigation, breaker, or overlap information.

## Conclusion

EXP-012 cannot be performed honestly from the archived baseline artifacts.

No Order Block classification rule will be inferred or invented.

A future OB experiment would require deterministic historical features such as:

- bullish / bearish OB creation;
- OB high / low boundaries;
- active / invalidated state;
- first retest timestamp;
- mitigation / hold / failure;
- breaker conversion;
- distance from signal to OB;
- FVG overlap.

Producing those fields would require a separate historical feature-enrichment project.

That work is outside the current diagnostic baseline decomposition and does not justify rerunning the historical pipeline now.

## Decision

**BLOCKED — NO STRATEGY CONCLUSION.**

EXP-012 provides no evidence for or against Order Blocks.

Proceed to [[EXP-013-Premium-Discount]].
