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
- Draft PR #7 on `research/pre-critical-integrity` is the single active
  integration branch for the execution/accounting/data-integrity gate.
- `research/r70-continuation-displacement` is a preserved historical research
  branch. Its completed R5-R7 archives are reconciled into canonical history;
  the branch remains for provenance.
- R7.0 completed across 2023/2024/2025 and was rejected as a production
  qualification rule. Further R7 selection research is paused until PR #7's
  integrity gate is cleared.
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

PR #7's engineering implementation and 2023–2025 execution-evidence archive
closeout are verified; the checkpoint is ready for review with documented limits.
See `docs/integrity_closeout_20261009.md`. Actual account fees are required before
realistic net-performance claims, not accounting-engine verification. The optional
liquidity-policy proposal is deferred. Do not restart completed R5/R6/R7.0 studies.
After the reviewed integrity checkpoint is merged to `main`, sync Voyages and
only then preregister the next isolated R7 interaction.

## Branch cleanup policy

Do not delete preserved research branches yet. After PR #7 is merged:

- verify every unique archive/document needed for provenance exists on main;
- review `perf/scoring-streaming-memory` separately;
- confirm old merged/superseded branches contain no unique required work;
- then prune obsolete remote branches in one dedicated cleanup pass.
