# R7 control feasibility and next step — 2026-10-09

Status: preparation resumed; statistical selection is blocked by an empty corrected
control. R7.0 is already complete and rejected; it is not rerun.

## Executable control

Use fvg_chronology_v2 and market_after_retest_confirmation_v2 as the corrected
control identity, with the frozen effective config and input/output identities
in the three EXP-INTEGRITY-{year}-DIAGNOSTIC archives. No legacy score-only,
fixed-target or zone-hypothesis control is substituted. No candidate trading rule
has been selected or implemented at this checkpoint.

The archived-evidence preflight is `scripts/check_r7_control.py`. It verifies
both lock identity digests, input/output artifact correspondence, exported output
hashes/sizes and counts. It prints its report and returns exit code 2 for an empty
control. Code/config/source features are not changed by the check. This is an
explicit preflight tool, not a claim that every historical research runner has
been migrated to it. Coverage-present status alone never certifies readiness.

## Observed qualification coverage

| Year | Score-candidate rows | Eligible directional signals | Accepted plans | Trades |
| --- | ---: | ---: | ---: | ---: |
| 2023 | 659 | 7 | 0 | 0 |
| 2024 | 697 | 2 | 0 | 0 |
| 2025 | 846 | 7 | 0 | 0 |

Score rows and directional signals are different units. Rejection causes overlap.
Among the sixteen eligible signals, thirteen fail structural risk; fourteen fail
first-obstacle room, and thirteen fail TP1 asymmetry. One signal's next-open fill
is outside the entry window. These totals do not identify why the preceding
score-candidate rows failed confirmation qualification.

See r7_control_coverage.json for per-year counts, causes and exact identities.
A candidate that only adds eligibility filters cannot create an accepted plan
from the zero-accepted-plan control. Running that comparison would provide no
performance evidence. Zero trades is not automatically a bug or justification
to lower requirements. Previously archived profitable controls use different
entry/sequence/stop/target semantics and cannot resolve this issue by substitution.

## Completed qualification diagnosis

The received 2023 export was decoded, checked and archived as
`research-archive/EXP-INTEGRITY-2023-QUALIFICATION`. All 659 candidates are unique,
completed, within the entry window and on the expected contract segments. The
current production qualification APIs reproduce the archived seven signal keys,
families and confirmation FVG identities exactly.

| Earliest qualification outcome | Rows |
| --- | ---: |
| Selected family has no active sequence | 640 |
| Selected family has active sequence but no fresh confirmation event | 12 |
| Qualified signal | 7 |

Family selection gives 566 reversals and 93 continuations. One short candidate on
2023-08-24 at 13:45 UTC has a continuation event but recent buy-side sweep selects
reversal. This is consistent with the written family precedence and shared API;
it is not a demonstrated implementation mismatch or evidence of a valid missed
trade. No family fallback or trading-rule change is made.

## Completed causal-window diagnosis and next decision

The requested export is received and archived at
`research-archive/EXP-INTEGRITY-2023-CAUSAL-WINDOWS`. Both 31-minute windows are
consecutive completed bars with start-plus-one-minute availability. All three
candidate rows agree with the previous export. The production chronology core
loop, observed with the object-linkage boundary stubbed, has no completed reversal
core in either window. Full FVG objects were not supplied; this is not a lifecycle
replay or a proof covering all 640 inactive yearly candidates.

January 3: the earlier sell-side sweep expires, and the new sweep shares a minute
with displacement/MSS, which does not satisfy the earlier-sweep requirement.
August 24: the early MSS precedes the later displacement, no subsequent MSS
completes that core, and the newest sweep has no later raw displacement/MSS. The
13:45 continuation nevertheless confirms, but existing family precedence selects
reversal. These samples match the documented rules; no code fix is established.

Stop requesting the same diagnostic flags or rerunning yearly builds. The next
step is a strategy decision, not another data repair: review the concrete isolated
`confirmation_first_family_v1` proposal in
`docs/research/r7_family_policy_proposal.md`. It would select a fully confirmed
continuation when no fully confirmed reversal is ready, retaining reversal
precedence when both confirm. On the supplied 2023 flags it adds only one qualified
candidate (seven to eight); plan acceptance and profitability remain unknown.

The user approved the proposal, and it is implemented/tested as an explicit
research option. It is a qualification diagnostic variant, not a statistical
performance experiment. Keep all risk,
obstacle, score, target and chronology requirements unchanged. No additional VPS
export is required for this decision. Full meaningful R7 selection remains pending.

## Execution boundary

No research experiment, historical profitability comparison or production
promotion was run. Read-only diagnosis can continue under the user's instruction
to proceed with R7. Remote experiment execution requires explicit authorization
under RULES.md section 17 after a concrete candidate/control is prepared.

## Validation

Focused preflight/identity tests: 14 passed. Full combined suite: **805 passed,
872 warnings in 25.35 seconds**. Drift in any exported output and a forged lock
identity are rejected before a coverage claim. The actual immutable three-year
archives produce BLOCKED_EMPTY_CONTROL; CLI exit code 2 is expected for that
result. No new feature generation or statistical backtest was run.

The qualification evidence passes decoded payload SHA-256, three archive file
hashes, candidate schema/count/uniqueness checks, and exact production API signal
and FVG identity reproduction. The documented read-only export command was
validated against two temporary Parquets: 62 window rows round-trip and outside
rows are excluded. No production code changed, so the 805-test suite was not
repeated. The temporary pandas fixture emitted one NumPy timedelta deprecation
warning; no fixture or generated data was committed.

Causal-window validation: 62 rows decoded; uniqueness, completion, availability,
window continuity and all three overlapping candidate rows checked; real chronology
core loop inspected with an explicitly stubbed linkage boundary; all archive
hashes verified. Proposal-only flag arithmetic preserves the seven existing
qualifications and adds one continuation. No executable production code changed;
the last full code baseline remains 805 passed, 872 warnings, without a redundant
suite rerun.


## Current next action after approval

Research option `confirmation_first_family_v1` is implemented. The 824-test full
suite passes; default behavior remains unchanged. EXP-030 is prepared to evaluate
the added 2023 continuation against preserved control evidence, without rebuilding
features or rerunning the empty control. See
`docs/research/r7_family_policy_implementation.md`. Remote execution requires an
explicit run instruction; the request file remains idle. No further export is
needed before that authorization, and no historical acceptance/P&L is claimed.
