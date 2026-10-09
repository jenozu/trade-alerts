# Experiment preparation status — 2026-10-09

## Checkpoint and execution boundary

Audited canonical `main` at `12f714a37eae5891a452e4608da09d7b732c2156`.
The working tree was clean, and GitHub had no open pull requests at inspection.
This record is a preparation audit, not an experiment result or a completed
five-experiment implementation batch. No new experiment IDs have been assigned.

No VPS connection, experiment wrapper invocation, historical experiment run,
live-system access or trade occurred. `run-requests/current.json` remains the
original idle request; SHA-256:
`72a02a1e5c34891cc1f7ab54d1592697cb4eaa16636f3b88119cd22bb9d0898c`.

## Sources and conflict resolution

Follow `REPOSITORY_STATE.md`: merged main implementation, reviewed open PRs,
`phases.md`, `refine-roadmap.md`, archives, then historical branches.
Also read `RULES.md`, `CHATGPT_COMMANDS.md`, the research index, experiment notes,
resume-readiness and integrity-closeout records, R7 control/proposal/implementation
documents, runners, shared research modules, tests and automation.

There is no separate experiment registry or master-plan file assigning future
numeric IDs. `refine-roadmap.md` is the detailed research plan; `phases.md` is the
milestone checklist. Numeric EXP IDs and phase/subtask IDs are distinct.
The command example `prepare 22` does not define EXP-022.

Earlier next-step statements are historical: section 19 of `refine-roadmap.md`
still says to begin EXP-007, and the old research-index introduction calls EXP-002
next. Completed archives and current canonical milestones supersede those
statements. Current R7 implementation instructions supersede the earlier
causal-export/approval requests. Preserve their historical evidence rather than
rerunning work.

## Inventory

| Experiment or phase | Recorded state | Preparation/execution action |
| --- | --- | --- |
| EXP-001–EXP-011 | Historical results and manifests archived; Python runners exist | Preserve; do not rerun or migrate results to corrected semantics. Only EXP-001 has a remote wrapper in this range. |
| EXP-012 | Explicitly blocked in roadmap and experiment note | Cannot prepare honest OB analysis without specified deterministic OB features and historical feature enrichment. |
| EXP-013–EXP-021 | Historical results and manifests archived; Python runners exist | Preserve; no remaining execution implied. Remote wrappers are absent for these completed studies. |
| EXP-022–EXP-029 | No assigned experiment definitions found on main | Do not infer an ID mapping from R4–R6 or the shorthand examples. |
| R4 development scoring/threshold research | Milestone records completion | Preserve historical candidates; no scoring change. See archive discrepancy below. |
| R5.0–R5.3 | Completed evidence reconciled on main | Do not rerun. |
| R6.0–R6.3 | Completed evidence reconciled on main | Do not rerun. |
| R7.0 / R7-00 | Completed and rejected for production | Rejection is completed research, not unprepared work. |
| EXP-030 | Prepared, not executed | Existing reviewed wrapper and opt-in family-policy implementation; diagnostic review still pending. |
| Later R7 interactions | Not preregistered; dependency blocked | Review EXP-030 before defining a larger comparison. |
| R8 | Conceptual regime/day-type objectives only | Needs explicit causal classifiers/boundaries and locked applicable control/candidate inputs. |
| R9 | Conceptual robustness objectives only | Needs frozen candidates, sensitivity grids, outlier policy and actual cost assumptions. |
| R10 | Conceptual held-out/walk-forward objectives only | Needs approved data splits/windows and model freeze. 2026 is pseudo out of sample, not an untouched holdout. |
| R11 | Conceptual final comparison objectives only | Depends on independently supported candidates and R9/R10 evidence. |
| R12 | Production acceptance checklist | Depends on preceding evidence and shadow/live observations; preparation does not authorize deployment. |
| EXP-031 onward | No definitions found on main | No legitimate first batch of five can be selected yet. |

`phases.md` labels R2 completed at milestone level, but EXP-012 remains explicitly
blocked. Retain that exception rather than claiming all R2 experiments ran.
`refine-roadmap.md` records R4.6 completion and names `research-archive/R4-06/`,
but that directory is absent from the audited main tree. This audit does not
recover the evidence or overturn the higher-priority R4 milestone. Record the
missing archive as a provenance limitation before relying on those candidates;
do not regenerate research merely to fill it.

## Existing EXP-030 contract

- Objective: evaluate the added 2023 continuation under the already approved
  `confirmation_first_family_v1`; diagnostic only, not statistical selection.
- Wrapper: `automation/experiments/EXP-030.sh`.
- Runner: `scripts/audit_linked_execution.py`; control verifier:
  `scripts/check_r7_control.py`; tests include
  `test_confirmation_family_policy.py`, `test_linked_execution_audit.py`,
  `test_r7_control_coverage.py` and `test_automation_commands.py`.
- Config: `research-archive/EXP-030-PREPARATION/RESEARCH_OPTION.yaml` contains
  opt-in settings only. The runner preserves the original full strategy and
  changes only family policy; do not replace `config/strategy.yaml` with it.
- VPS source:
  `/root/trade-alerts-verify-YwIqEc/replays/isolated-2023-xgi4yfiw/chronology`.
  Required summary, lock, original configs and locked segment features must
  exist and match identities. Their present availability is not verified here.
- Environment supplied by the existing dispatcher: `PYTHON_BIN`,
  `TRADE_ALERTS_PROJECT_ROOT`, `AUTOMATION_RUN_DIR`, `AUTOMATION_GIT_SHA`.
- Output: fresh sibling `EXP-030-<Git SHA>-<request ID>`; existing output paths
  are refused. Evidence includes `FAMILY_POLICY_COMPARISON.json`,
  `EXECUTION_AUDIT_SUMMARY.json`, `decisions.json`, `effective_strategy.yaml`,
  both experiment locks and optional `diagnostic_trades.csv`.
- Comparisons require identical feature identities, config differing only by
  family policy, seven unchanged prior decisions and exactly the specified
  additional NMU23 short signal at 2023-08-24 13:45 UTC.
- `set -euo pipefail` propagates command/comparison failures. The existing
  dispatcher captures the log, exact SHA, status and exit code in its manifest.
  No new exit-code contract is introduced by this audit.

## Actual preparation blockers

The corrected control has zero accepted plans in all three development years.
The approved diagnostic adds one qualification, but accepted execution and P&L
are unknown. The current implementation document explicitly requires reviewing
the diagnostic before preparing a larger comparison. A filter-only candidate
cannot create accepted trades from this control.

Therefore there are fewer than five specified, independent unprepared
experiments. Do not create EXP-031–EXP-035 from conceptual bullet points or
silently choose a replacement control, classifier, parameter grid, cost model,
holdout split or success threshold. `RULES.md` sections 2, 6 and 15 and the user's
preparation instructions require these semantics to be specified first.

To resume implementation, supply either an existing approved registry/specification
that is missing from main, or reviewed EXP-030 evidence followed by approved
preregistrations. Each must assign an ID, dependencies, executable control and
candidate, exact changed settings, inputs, metrics and decision criteria. Run
authorization remains separate and is not requested or inferred by this record.

## Safe continuation

1. Fetch main and inspect open PRs/working tree before writing.
2. Read this record and current R7 implementation/next-step documents.
3. Preserve all completed archives and the idle request.
4. Resolve specifications/dependencies above; do not repeat diagnostic exports
   or yearly pipelines.
5. Once five independent specified unprepared experiments exist, prepare them
   in dependency order, validate, commit/push and update this record.
6. Record each batch's exact commit SHA, IDs, checks and limitations in its
   status entry. No batch is completed at this audit checkpoint.

## Available preparation checks

Checks on the audited code, using a project-local Python 3.12 venv with the
unchanged requirements:

- Full suite: **824 passed, 967 warnings in 25.79 seconds** using
  `.venv/bin/python -m pytest -q --maxfail=1`. Existing NumPy timedelta/pandas
  compatibility warnings remain; none were suppressed or fixed in this audit.
- `bash -n`: both existing EXP-001 and EXP-030 wrappers pass.
- AST syntax: EXP-030 embedded comparator and both automation entrypoints,
  execution auditor and R7 control checker pass.
- Both wrappers reference existing Python entrypoints.
- Workflow parsed: dispatch is restricted to pushes changing
  `run-requests/current.json` on main. Preparation documents cannot trigger it.
- Idle request action and exact bytes checked; no modification.
- `git diff --check` passes.
- ShellCheck, dedicated linter and type checker are unavailable in this checkout;
  none are configured in the repository. Their checks are not claimed.

Static checks and synthetic tests are preparation checks, not historical execution.
No VPS files or GitHub Actions SSH execution can be certified without running
the separately authorized workflow.
