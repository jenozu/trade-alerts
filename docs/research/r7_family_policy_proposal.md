# R7 family policy — approved research option

Status: the user approved implementation/testing on 2026-10-09. The variant is
implemented as an explicit research opt-in; defaults, source data and historical
archives are preserved. Remote execution has not been authorized or requested.

## Observed problem

The corrected 2023–2025 control has zero accepted plans. A filter-only interaction
cannot produce useful performance evidence from that control. The 2023 candidate
flags reproduce the archived qualification decisions, and two causal minute
windows show nonqualification consistent with the selected chronology rules.
This bounded diagnosis establishes no implementation defect in those samples.
It does not certify all historical sequences or invalidate the stored raw data.

At 2023-08-24 13:45 UTC a completed short continuation is blocked by recent
buy-side sweep context selecting an unconfirmed reversal. The existing rule is
documented, so replacing it is a strategy choice, not a bug fix.

## Recommended isolated diagnostic variant

Name: `confirmation_first_family_v1`.

For each eligible direction, after the existing completion and entry-window
checks:

1. Reversal is ready only when its selected chronology sequence is active AND
   its fresh entry-valid event is true.
2. Continuation is ready under the same active-sequence AND fresh-event test.
3. Select reversal when both are ready; otherwise select the ready family.
4. When neither is ready, do not qualify the direction.

Recent/raw sweep context does not veto an otherwise fully confirmed continuation.
The reversal sequence still requires its initiating raw sweep. Both families
retain their current chronology, FVG identity, expiry and invalidation requirements.
Completion, score eligibility, side ties, entry timing, slippage, structural
risk cap, obstacle room, targets and position management all remain unchanged.
Keep the existing context-first policy as the default and diagnostic control;
the implemented variant requires an explicit research opt-in.

## Known impact and limits

Read-only flag arithmetic on all 659 supplied 2023 candidates yields seven
current qualified signals versus eight under the proposal. The only additional
candidate is the short continuation above. Existing seven signal families remain
unchanged. This historical flag calculation has not called the planner or simulator for the
extra candidate. Synthetic tests do exercise accepted planner/backtest paths in
both directions under the new policy. It is not an accepted trade, P&L estimate, statistical result,
optimization finding or justification for production promotion.

This is a qualification/decision diagnostic, not a meaningful profitability
interaction experiment. The variant might also accept no plans, and even one
additional trade would not establish a useful sample. Do not automatically
relax another rule if it also fails. Current zero-plan evidence remains intact.

## Implemented and prepared work

Implement one versioned shared family selector used consistently by the opted-in
planner and backtester. Test both-ready precedence, continuation-only readiness,
fresh-event requirements, unknown policy rejection and unchanged default behavior.
Run relevant tests and the full suite, inspect the diff, then commit and verify.
Prepare a locked, narrowly scoped eligibility/decision comparison using existing
2023 features, with separate output paths. That remote diagnostic needs its own
explicit run authorization under RULES.md section 17. Do not rerun R5/R6/R7.0
or rebuild upstream features. Review qualification and plan-rejection counts
before deciding whether a larger research comparison is warranted.

## Approval boundary

RULES.md section 6 says: "An engineering agent may fix implementation errors
autonomously, but it must not invent trading semantics." This proposal changes
which setup can qualify and is not specified by the source strategy's broad
reversal/continuation descriptions. The user approved implementing and testing this named
variant. There is no approval request to weaken data integrity or deploy it live.


## Verified implementation checkpoint

Set `backtest.family_policy: confirmation_first_family_v1` together with market
execution v2 and chronology v2. Unknown policy names and incompatible modes fail
closed. Omission keeps `context_first_family_v1` and preserves current behavior.
The opted-in market planner and backtester share the family selector, including
candidate family labels and confirmation FVG identity. Audit input/output locks
record effective policy and configuration under a separate diagnostic identity.

Focused execution/chronology compatibility tests: 122 passed. Full regression:
824 passed, 967 compatibility/deprecation warnings in 58.20 seconds. Synthetic
accepted trades reproduce independent plan JSON in both directions; future
extremes do not change entry decisions. The real 659-row archived flags give
seven default qualifications and eight opted-in qualifications, with only the
identified August 24 continuation added. Historical acceptance/P&L is unknown.

Prepared reviewed wrapper: `automation/experiments/EXP-030.sh`. It reuses verified
archived control evidence, evaluates only the opted-in 2023 diagnostic on existing
chronology features, compares identical source hashes/configuration, and requires
the original seven planner decisions to remain unchanged. New outputs use a fresh
sibling directory. Comparator fixtures reject altered existing decisions. It is
not a performance selection run and does not rebuild upstream features. The run
request remains idle. An explicit `run EXP-030` is required under RULES.md section
17 before remote execution. See `docs/research/r7_family_policy_implementation.md`.
