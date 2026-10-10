# Repository State — Trade Alerts

**Updated:** 2026-10-09  
**Canonical stable branch:** `main`  
**Visual roadmap source:** `main/phases.md`

This file exists so multiple ChatGPT conversations, local VPS sessions and
research branches do not drift into competing versions of the project.

## Current state

- `main` is the stable source of truth for completed project state.
- Voyages reads `main/phases.md`; if that file is stale, the visual percentage
  is stale even when work exists elsewhere.
- PR #7 is merged at `4b947ebc3eca0f1e3e37af689e262cd622e67025`.
  The qualified engineering checkpoint and yearly execution archive are complete;
  `research/pre-critical-integrity` remains preserved for provenance.
- `research/r70-continuation-displacement` is a preserved historical research
  branch. Its completed R5-R7 archives are reconciled into canonical history;
  the branch remains for provenance.
- R7.0 completed across 2023/2024/2025 and was rejected as a production
  qualification rule. Next R7 preparation must identify its executable control
  and candidate contracts before any selection run.
- `perf/scoring-streaming-memory` contains two unique historical optimization
  commits that are not on main and have no PR. Preserve it for later review;
  do not silently merge or delete it.
- Other completed performance/fix branches whose tips are behind main are
  historical branch pointers, not missing project work.

## Source-of-truth order

When facts conflict, use this order:

1. `main` for stable merged implementation.
2. Open reviewed integration PRs for work not yet merged.
3. `phases.md` for canonical project milestone state.
4. `refine-roadmap.md` for detailed strategy-research evidence and decisions.
5. `research-archive/` for immutable experiment artifacts.
6. Historical branch tips only for provenance or recovery.

A commit existing on a historical branch does not by itself mean production or
the canonical roadmap should change.

## Cross-conversation write rule

Before any conversation writes to GitHub:

1. fetch current `main`;
2. inspect open PRs and the active branch;
3. fetch the target branch head immediately before writing;
4. use fast-forward / expected-head semantics;
5. if the head moved, reconcile the new commit instead of overwriting it.

Do not have two conversations independently force-push or rewrite the same
branch. If another conversation is actively changing the integration branch,
use a separate short-lived branch and reconcile through a PR.

## Experiment closeout rule

A research experiment is not considered fully reconciled until all applicable
steps are complete:

1. targeted tests;
2. chronological yearly runs and control parity;
3. archived outputs and hashes/review artifacts;
4. decision recorded in `refine-roadmap.md`;
5. milestone status reflected in `phases.md`;
6. commits pushed;
7. canonical evidence merged to `main`;
8. Voyages synced.

Rejected experiments count as completed research. Rejected means "do not promote
the rule", not "the work is unfinished".

## Current approved next action

**2026-10-10 data acceptance priority:** The user requested a pause in further
research selection to verify same-contract history and source coverage across
2023–2025. Independent-contract builds are already complete; their supplied
stitched inputs may still omit earlier history present in individual downloads.
The read-only inventory implementation and ordered remaining work are recorded
in `docs/contract_history_inventory.md`. Actual VPS inventory/coverage acceptance
is pending. Do not claim universal data integrity or repeat yearly builds without
an identified affected source. This does not change the separately authorized
EXP-030 request; its diagnostic cannot certify historical coverage.

The remaining-experiment preparation audit is recorded in
`docs/research/experiment_preparation_status.md`. EXP-030 is already prepared;
main assigns no definitions to EXP-031 onward. No new batch or execution is
claimed. Continue from approved specifications and preserve the R7 diagnostic
review dependency described below.
EXP-030's execution/setup checklist and proposed R7–R12 specification backlog
are in `docs/research/exp030_readiness_and_backlog.md`. Code is prepared; SSH/VPS
operational readiness is not yet verified. No new experiment or run request is
created by this documentation.

PR #7 is merged and the canonical phases.md records the completed qualified
engineering checkpoint. Final regression: 800 passed, 872 warnings. Preserve
its accepted-path, fee, upstream-provenance and deployment limits in
`docs/integrity_closeout_20261009.md`. The liquidity-policy proposal is deferred.

R7 preparation has resumed. Its corrected-control feasibility check is recorded
in `docs/research/r7_next_step.md`; additional eligibility filters cannot be
evaluated on this zero-accepted-plan control. The 2023 flags are now archived
and the current APIs reproduce all seven
archived signal/FVG identities. Two causal minute windows are now archived and
sampled nonqualification follows current rules; no implementation defect is
established by these samples. The user approved the research-only confirmation-first
family option, now implemented with 824 passing tests. Defaults and source data
are preserved. EXP-030 is prepared to evaluate the 2023 added continuation while
reusing locked control evidence. It requires explicit run authorization; the run
request remains idle. See `docs/research/r7_family_policy_implementation.md`.
Historical acceptance/P&L and meaningful statistical selection remain pending.
Do not rerun
R5/R6/R7.0. Remote experiment execution still requires an explicit run command
under RULES.md section 17. No live deployment is implied.

Voyages fetches main/phases.md without a server cache; the next app refresh reads
this checkpoint. No displayed percentage or user-browser refresh is claimed here.

## Branch cleanup policy

Do not delete preserved research branches yet. After PR #7 is merged:

- verify every unique archive/document needed for provenance exists on main;
- review `perf/scoring-streaming-memory` separately;
- confirm old merged/superseded branches contain no unique required work;
- then prune obsolete remote branches in one dedicated cleanup pass.
