# R7 family policy proposal — pending strategy approval

Status: reviewable proposal only. No executable rule, configuration, production
default or historical archive is changed. No remote experiment is requested.

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
implement this variant only as an explicit research opt-in if approved.

## Known impact and limits

Read-only flag arithmetic on all 659 supplied 2023 candidates yields seven
current qualified signals versus eight under the proposal. The only additional
candidate is the short continuation above. Existing seven signal families remain
unchanged. This calculation has not called the planner or simulator for the
extra candidate. It is not an accepted trade, P&L estimate, statistical result,
optimization finding or justification for production promotion.

This is a qualification/decision diagnostic, not a meaningful profitability
interaction experiment. The variant might also accept no plans, and even one
additional trade would not establish a useful sample. Do not automatically
relax another rule if it also fails. Current zero-plan evidence remains intact.

## Work after approval

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
reversal/continuation descriptions. Approval is needed to implement this named
variant. There is no approval request to weaken data integrity or deploy it live.
