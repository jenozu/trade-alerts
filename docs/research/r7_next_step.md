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

## Next required evidence

Inspect the score-candidate rows from existing 2023 chronology features, starting
with completion/window flags, directional sweep/family precedence and linked
sequence/event flags. Use a read-only export, not another feature build or
execution simulation. Source feature files reside on the VPS and are not present
in Work. Local analysis of that export can identify the qualification stages
responsible for lost opportunities; the sixteen archived decisions already
explain the final planner rejections.

First determine whether this is expected qualification or an implementation
mismatch. Fix only proven mismatches. Any rule relaxation, new liquidity classifier
or different executable control is a separately named strategy decision under
RULES.md section 6; it is not authorized by the desire to obtain trades.

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
