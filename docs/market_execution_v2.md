# Confirmed market execution v2

This opt-in integrity version shares the production planner's structural risk,
obstacle and liquidity-objective construction. It is not selected from historical
profitability and does not change score weights or thresholds.

## Decision contract

The selected next-minute-open entry remains. Freeze the completed confirmation
state; the observed immediately following minute open plus adverse slippage is
the execution reference. Do not include that minute's high, low, close or features
in the decision. Check both explicit signal eligibility and fill time within
09:30 inclusive to 10:30 exclusive America/New_York, including DST.

`trade_planner.build_market_execution_plan` is the shared public decision API.
It requires a completed state, directional candidate and fresh entry event for
the selected production family. It calls the existing planner construction with
the market execution reference. Trigger-zone geometry stays recorded as context;
it no longer substitutes for an executed entry when computing risk or distances.
The existing `build_trade_plan` API continues to produce zone-based hypotheses.
It is not an execution decision and should not be compared as if it were a fill.

Use the planner's protected swing and configured structural buffer. Reject missing,
wrong-side or oversized structure; never pull the stop inside invalidation or
substitute a fixed stop. Initial price risk must be positive and no more than
25 points (or the smaller configured preferred maximum). The attached strategy
explicitly says 25-point maximum and to put stops beyond invalidating structure.
Smaller valid structural risk is permitted and retains the planner's downgrade
outside the preferred 20–25 range. Fees and adverse stop gaps can exceed initial
price risk; this is not a guaranteed loss cap.

Use the existing planner's directional objective filtering, minimum room and
reward/risk checks, recalculated relative to executed entry. Levels already passed
in the trade direction are not obstacles ahead. Preserve ranked DOL and liquidity
targets; do not manufacture fixed-distance replacements or round off source levels.
TP1 and TP3 are required by the planner; TP2 is optional. TP4 must exist for the
current full-position runner policy. Missing TP4 means NO TRADE rather than a
silent exit-policy switch. This fail-closed case is reported explicitly and needs
review if an alternative primary-DOL terminal policy is desired later.

Management remains the current configured full-position exit at TP4, structural
stop, 60-minute timeout or end of sample. Earlier targets are observations.
Conservative opening-gap handling, stop-first OHLC ambiguity, commissions and
adverse slippage remain. Only structural-stop invalidation is executable in this
version; other planner invalidation descriptions are retained separately as
planned criteria, not falsely represented as automated exits.

## Boundaries

The old score-only and confirmed-v1 versions and their ledgers remain reproducible.
V2 does not certify upstream sequence-object linkage or same-row reversal order,
introduce EMA/Kumo/SMT/OB requirements, implement partial/breakeven management,
or establish real-data source/rollover parity. These remain independent audit
tasks. No existing cache or archive may be overwritten to adopt this version.

Planner API verification adds 16 positive/rejected cases, including
both families/directions, passing an old obstacle, rejection instead of fixed-stop
fallback, timing/window boundaries and missing runner/evidence. This is synthetic
contract evidence; a new isolated historical replay remains required.

API checkpoint: focused planner suite 26 passed, 5 warnings; full regression
666 passed, 443 warnings in 12.96 seconds. Existing zone-planner contracts remain
green. The backtest integration is a subsequent sequential task.
