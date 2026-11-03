# ROADMAP — prioritized work view (2026-11-02)

> **This is a priority view, not a second source of truth.** The canonical milestone
> checklist is `phases.md` (Voyages reads it). Detailed research decisions are in
> `refine-roadmap.md`. The provisional EXP-031–050 registry is
> `docs/research/proposed_experiment_registry_r7_r12.md`. If this file disagrees with
> those, they win. Update this file only when priorities change.

Evidence and reasoning: `PROJECT_STATUS.md`.

Rules that apply to every task: `RULES.md`. In particular, no look-ahead (§2), escalate
strategy ambiguity (§6), archive everything (§16), and execute only on an explicit `run N` (§17).

---

## Phase 1 — Repository recovery and infrastructure *(mostly done)*

| # | Task | Status | Done when |
|---|---|---|---|
| 1.1 | Audit repository, history, automation | **Done 2026-11-02** | `PROJECT_STATUS.md` exists |
| 1.2 | Verify GitHub Actions → VPS SSH | **Done** (run 38062346882 green, 2026-10-10) | — |
| 1.3 | **Save + archive EXP-030 run record** | **URGENT**: artifact expires ~2026-11-09 | `research-archive/EXP-030/` with manifest; result reviewed |
| 1.4 | Reconcile stale docs (`phases.md`, `REPOSITORY_STATE.md`, Research-Index) with EXP-030 reality | Todo | Docs agree with Actions history |
| 1.5 | Decide the master-prompt conflicts (PROJECT_STATUS §11) | Needs your input | Decisions recorded in `REPOSITORY_STATE.md` |

## Phase 2 — Historical data integrity *(current priority)*

| # | Task | Status | Done when |
|---|---|---|---|
| 2.1 | Report Barchart repair download status (`download_history_repairs.py status`) | **Needs you** | Progress log reviewed |
| 2.2 | Finish the remaining repair downloads (13 incoming contracts, 56 days pre-roll) | Unknown | All requests `VERIFIED` in `progress.jsonl` |
| 2.3 | Validate repaired files against the existing contract files (exact overlap match) | Todo | Overlap report: zero mismatches or explained |
| 2.4 | Confirm or refute the roll-weekend Sunday-session hole (7 contracts) | Todo | Finding documented |
| 2.5 | Classify sessions against the CME calendar (holidays, DST, maintenance breaks, no-trade minutes) | Todo | Session report per contract |
| 2.6 | Build **new, versioned** contract segments with real pre-roll warm-up; never overwrite the old ones | Todo | New feature-build locks; old locks preserved |
| 2.7 | Publish the data coverage report: earliest/latest, usable days, bars, missing intervals, contracts, rollover dates, warnings | Todo | `docs/data_coverage_report.md` + JSON |
| 2.8 | Extend acquisition past 2026-09-04 (needed for any real forward holdout) | Later | — |

## Phase 3 — Backtesting reliability

| # | Task | Status |
|---|---|---|
| 3.1 | Re-run the corrected 2023–2025 diagnostics on repaired data (explicit `run` required); compare signal and accepted-plan counts to the archived zero-trade control | After 2.6 |
| 3.2 | **Strategy decision:** review the rejection causes (structural risk, first-obstacle room, TP1 asymmetry) and decide whether they match how you actually trade | Needs you |
| 3.3 | Document account MNQ commissions/fees; enable net accounting | Needs you |
| 3.4 | Specify limit/retest and stop/breakout fill models; same-bar ordering policy using finer data where it exists | Spec first |
| 3.5 | Freeze a trade-producing baseline (config + code + data identity) | After 3.1–3.4 |
| 3.6 | Fix NumPy generic-timedelta deprecations (968 warnings) before they become errors | Any time; small |

## Phase 4 — Experiment infrastructure

- 4.1 Auto-archive run records: have the workflow open a PR that copies the run record into `research-archive/` (no direct push to `main`).
- 4.2 Config-driven parameter sweep runner (`sweep`, not `batch`): controlled grids, fixed seeds, per-variant locks, ranked report.
- 4.3 Standard per-run report: equity and drawdown curves, MAE/MFE, target hit rates, comparisons by setup, time, weekday, direction and regime, parent and baseline comparison.
- 4.4 Review/merge the draft EXP-031–050 specification PRs (#10–#13) once 3.5 exists.

## Phase 5 — Autonomous research

- 5.1 Walk-forward runner and an untouched holdout. Per `research_dataset_policy.md`, this needs a preregistered future period.
- 5.2 Research journal automation on top of `trade-brain/40-Research/` (hypothesis → prediction → result → generalized?).
- 5.3 Promotion gates as code: a candidate is promoted only through a reviewable PR, never by silently replacing the baseline.

## Phase 6 — Continuous automation

- 6.1 Pin the VPS host key; update deprecated actions; check the Ubuntu 26 runner.
- 6.2 Read-only `status N` / `logs N` / `results N` helpers.
- 6.3 Scheduled cheap checks (tests, data integrity) kept separate from budgeted research jobs.
- 6.4 Notifications (Telegram transport already exists).
- 6.5 Dashboard: last, per your instruction.

---

## Single most important next task

**2.1–2.7: close the data acceptance gate**, immediately after the 10-minute EXP-030
save (1.3). Reason: about 4 of every 5 contract segments currently evaluate with no warm-up
history, so no strategy result, including the zero-trade control, can be trusted yet.
