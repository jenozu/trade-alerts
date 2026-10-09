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

## Next required evidence

Candidate-only flags omit the preceding noncandidate minute bars, so they cannot
explain why the causal sequence engine is mostly inactive. Obtain two narrow
read-only windows from the existing 2023 chronology Parquets: the first long
candidate (2023-01-03 14:34 UTC), and the overlapping-family short candidate
(2023-08-24 13:45 UTC), with 30 preceding minutes each. These are diagnostic
samples, not representative performance estimates or complete FVG-lifecycle proof.

Run the command in `docs/research/r7_causal_window_export.md` from the isolated
VPS checkout. It only reads existing files and prints an encoded text payload.
No feature rebuild, new execution simulation or yearly test repeat is required.
Source Parquets remain on the VPS and cannot be independently inspected here.

Fix only proven implementation mismatches. Any rule relaxation, new liquidity
classifier or different executable control is a separately named strategy decision
under RULES.md section 6; no such decision is inferred from zero trades.

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
