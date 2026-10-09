# R7 confirmation-first family implementation — 2026-10-09

The user approved the isolated research variant after reviewing the causal-window
diagnosis. This checkpoint implements and tests that choice; it does not promote
it or certify historical performance. The corrected default control remains
context-first and has zero accepted plans across 2023–2025.

## Opt-in contract

```yaml
backtest:
  execution_model: market_after_retest_confirmation_v2
  sequence_contract: fvg_chronology_v2
  family_policy: confirmation_first_family_v1
```

Keep configuration unchanged to use the existing default. This option is limited
to market execution v2 with chronology v2. Unknown names and unsupported mode
combinations fail. A family qualifies only on an active chronology sequence AND
a fresh confirmation event; reversal wins when both qualify. A confirmed
continuation can qualify despite recent sweep context when reversal is not ready.
All completion, entry-window, score, FVG identity, sequence timing, risk, obstacle,
target, slippage and position-management requirements are preserved.

The shared selector is used at backtest qualification, direct simulation,
ledger family reporting, market execution planning and diagnostic decisions.
The planner passes the selected execution family through candidate construction,
so labels/criteria cannot silently revert to the context-first family. The opted-in
plan records its family policy. Legacy zone plans keep their existing semantics.

## Verification

- Initial regression reproduced the missing opted-in acceptance before the change.
- Focused execution/chronology suite: 122 passed, 504 warnings.
- Full suite: 824 passed, 967 warnings in 58.20 seconds.
- Long and short synthetic accepted continuations match independent planner JSON
  exactly, including actual next-open fill, structural stop and market targets.
- Existing default fixtures and all previous tests pass; default overlap still
  rejects the continuation, and both-ready research selection prefers reversal.
- Missing sequence/event, incomplete/window checks and invalid policy/mode reject.
- Future entry-bar extremes cannot change the opted-in entry decision.
- Locked audit fixtures cover unchanged source bytes, distinct effective policy
  identities, both verified locks and executed-plan parity in both directions.
- Actual 659 archived candidate flags retain the original seven qualifications and
  add only NMU23 short continuation at 2023-08-24 13:45 UTC.

Warnings include the existing NumPy timedelta and pandas compatibility deprecations.
Local venv uses pandas 2.3.3, NumPy 2.5.3, PyArrow 23.0.1, pytest 9.1.1; installed
within existing requirements ranges. No requirements or VPS dependencies changed.

## Prepared EXP-030 diagnostic

Reviewed wrapper: `automation/experiments/EXP-030.sh`. Source is the completed
`/root/trade-alerts-verify-YwIqEc/replays/isolated-2023-xgi4yfiw/chronology` build.
It requires the exact triggering Git SHA and a clean tracked checkout. The audit
verifies original producer blobs and unchanged source files, then uses only the
new explicit family policy. Outputs go to a fresh sibling path keyed by Git SHA
and request ID; existing directories are refused.

Reuse the existing locked control rather than running its yearly simulation again.
Compare variant input feature identities against that control and require the
configuration to differ only by family policy. The comparator requires all seven
original decision records to remain identical after removing the newly explicit
policy annotation; it then records the additional continuation's planner outcome.
This catches drift rather than silently mixing controls from different producers.
Small summary/config/decisions/lock artifacts are copied to the run evidence
directory. The comparison JSON records the reused control identity and scope.

Shell/embedded-Python syntax and synthetic comparator acceptance/drift rejection
were checked locally. The wrapper was not run against VPS data. `run-requests/
current.json` stays idle. An explicit run instruction is required by RULES.md
section 17; implementation approval does not dispatch a remote experiment.

No full yearly source build, R5/R6/R7.0 replay, 2026 tuning, production deployment,
or strategy-performance selection occurs. The added qualification may still fail
risk/obstacle/target checks. Even one accepted trade would not establish a useful
performance sample. Review the diagnostic before preparing any larger comparison;
do not automatically weaken another requirement if it also accepts zero plans.
