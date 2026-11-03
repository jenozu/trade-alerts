# MASTER-TASKS: Jangus × trade-alerts build plan

**Status:** DRAFT for owner approval. No task below is started or done.
**Created:** 2026-11-03, from the `main` commit `cd8e431`.
**Source:** "Jangus × trade-alerts Setup and Implementation Guide (draft for approval)", Nov 3 2026, Parts 2–8 and 10. Where the Autonomous Research Setup Guide (Nov 2 2026) differs, this plan follows the Setup Guide and says so.
**Plan of record:** this file. Once approved, it can be turned into the `.taskmaster/` PRD and `tasks.json` format if you want the Task Master tooling later.

---

## 0. How this plan is run

- **One task at a time.** Each task gets its own feature branch and pull request. Claude never works on `main`.
- **Claude may:** write code, tests, docs and drafts on feature branches; open draft pull requests; run targeted tests.
- **Claude may not, without your explicit approval:** merge anything, change `run-requests/current.json`, trigger a workflow that runs an experiment, touch the VPS, change `config/strategy.yaml` defaults, change `RULES.md`, `config/research_policy.yaml` or anything under `research-archive/`, or create or store any secret.
- **Your merge is the approval** for trade-alerts code and docs. Your written "go" in `MEMORY.md` (in Jangus) is the approval for each Jangus slice.
- **Status values:** `pending`, `in-progress`, `done`, `blocked`, `cancelled`. A task is `done` only when its "Done when" check has actually been run and its result recorded in the work log (section 9).
- **Drift rule:** an idea that is not on this list goes into section 10 (parking lot). It is not built until you add it here.

---

## 1. Goal and non-goals

**Goal.** Give research agents a safe, read-only way to ask trade-alerts questions (`scripts/agent_api.py`, a JSON command line). Then let a Jangus tool pack call it, so a zero-model report can run (milestone 1a). Then allow one tightly constrained model task (milestone 1b). Later milestones add draft pull requests, prepared experiments, approval-gated run requests and scheduling.

**Non-goals (all phases):**
- No broker connection and no orders. trade-alerts is research and alerts only.
- No agent changes a strategy rule, a promotion threshold or the approved baseline. Python computes every metric; language models never do.
- No agent reads holdout outcomes.
- No agent edits `research-archive/`, `RULES.md`, `phases.md` status or the research policy.
- No agent starts a VPS run. Only your merge of a run-request pull request does that.
- Jangus Phase 2b and later are not started until you authorize them.

---

## 2. Verified state at the start of this plan (2026-11-03)

Checked by reading the clone at `cd8e431`. Nothing was executed on the VPS or the PC.

| Item | Result |
| --- | --- |
| `main` commit | `cd8e431`, matches the Setup Guide's audit commit |
| `scripts/agent_api.py`, `docs/agent_api.md`, `tests/test_agent_api.py` | **Absent** (the work starts here) |
| `.github/workflows/` | Two files: `run-trade-experiment.yml`, `verify-barchart-repairs.yml`. **No `tests.yml`** |
| Run trigger | Push to `main` that changes `run-requests/current.json` (confirmed in the workflow file) |
| EXP-030 wrapper | Reads a source path under `/root/trade-alerts-verify-…` that exists only on the VPS. The archive step therefore has to run on the VPS (confirmed in `automation/experiments/EXP-030.sh`) |
| Archive | 27 `ARCHIVE_MANIFEST.json` files. **No `research-archive/EXP-030/`**; only `EXP-030-PREPARATION` exists |
| Python dependency | `PyYAML>=6.0.1,<7.0.0` is in `requirements.txt`, so `agent_api` can read YAML without a new dependency |
| Existing archive tests | `test_archive_experiment.py`, `test_research_archiver.py`, `test_verify_archive_r45.py`, `test_automation_commands.py` and others exist |
| Project rules file | There is no `CLAUDE.md` at the repo root. The governing rules are `RULES.md`, `CHATGPT_COMMANDS.md` and `REPOSITORY_STATE.md` |
| Remote branches | 19 branches on `origin`, including `docs/project-status-and-roadmap-20261103` (not merged). `PROJECT_STATUS.md` and `ROADMAP.md` are **not on `main`** |
| Research policy | `config/research_policy.yaml`: 2023–2025 development, 2026 pseudo-out-of-sample validation, forward holdout `not_established` |

**Not verified in this session** (these need your check or a later run):

- The full test suite. The earlier audit reported 867 passing tests on Linux with Python 3.13. Not re-run here.
- Whether the suite passes on Windows.
- The latest GitHub Actions runs, and whether run 38062346882's artifact still exists (GitHub deletes artifacts after 30 days, around Nov 9).
- Open pull requests on `jenozu/jangus`.
- VPS contents, user and SSH setup.
- Your PC: GPU, RAM, Jangus test results, Ollama models, Credential Manager.
- Barchart repair download status.
- The Jangus `docs/PHASES.md` scenario IDs (B08–B12 etc.) named in the Setup Guide. Those were taken from the guide and not re-read.

---

## 3. Decisions required before the gates (from Setup Guide Part 10)

| ID | Decision | Recommendation in the guide | Blocks |
| --- | --- | --- | --- |
| D1 | Authorize Jangus slice A, and when | Yes, once T1 is merged | J1 |
| D2 | Amend Jangus decision 15 so the read-only trading agent is the first to finish the 7-day soak | Yes | J1 |
| D3 | Where the trade tool pack lives | Jangus repo; `agent_api` contract stays in trade-alerts | J1 |
| D4 | How a run request is created | A pull request you merge, not a direct push | M4 |
| D5 | How run records are archived | On the VPS as a post-run step, then an archive pull request | M4 |
| D6 | Whether `trade-alerts` stays public | Decide before M2. It is public now, so notes and results are readable by anyone | M2 |
| D7 | Branch protection on `main` and the path guard | Yes, both | T2 |
| D8 | VPS hardening order: pinned host key, then forced-command key, then non-root account | Yes, in that order | T2, M4 |
| D9 | Research window for approved runs | Weekdays 17:00–08:00 ET and weekends, outside the 09:00–10:30 ET alert window | M4 |
| D10 | Local model choice, and whether to allow a Claude step-up | Pick from benchmark. No Claude until M3 proves it is needed | J2 |
| D11 | Whether the Windows PC is the long-term host | Yes for now | M5 |
| D12 | Keep, change or drop the `feature/tradingview-pinescript` branch | Decide before M3 | M3 |

**Strategy decisions (only you can make these; `RULES.md` §6).** They block M3.

- S-1: Are the corrected strategy's rejection rules (structural risk, first-obstacle room, TP1 asymmetry) right for how you trade? The corrected control accepted 0 of 16 eligible signals in 2023–2025.
- S-2: Your real MNQ commissions and fees. Commissions are off in the current config, so every net result is overstated.
- S-3: Promotion thresholds (minimum trades, out-of-sample margin, drawdown limit).
- S-4: The holdout period, set before anyone looks at its outcome.
- S-5: Whether VWAP and opening-range ideas become entry families (they are context only today).

---

## 4. Gates (places where work stops for you)

| Gate | What you decide | Unlocks |
| --- | --- | --- |
| G0 | Decisions D1–D12 that are relevant now, and S-2 | Phase T0 completion |
| G1 | Approve the `docs/agent_api.md` contract (T1.1), then merge T1 | T2 and J1 |
| G2 | Merge T2 and enable branch protection on `main` | M2 and any write tool |
| G3 | Written "go" for Jangus slice A (J1) in Jangus `MEMORY.md` | J1 work |
| G4 | Sign off milestone 1a after reading three reports | J2 |
| G5 | Written "go" for Jangus slice B (J2). Choose whether a Claude key exists | M1b |
| G6 | Sign off milestone 1b after a 7-day soak | M2 and later phases |
| G7 | Per-phase approval (M2–M5) and each run request | Each later phase |

---

## 5. Task list

### Phase T0: Housekeeping and decisions (this week)

Goal: remove the one time-boxed risk and settle what later phases depend on.

| ID | Task | Depends on | Owner | Done when |
| --- | --- | --- | --- | --- |
| T0.1 | Download the `EXP-030-r02-20261010-run-record` artifact from [run 38062346882](https://github.com/jenozu/trade-alerts/actions/runs/38062346882) while signed in, and attach it to the project chat. **Deadline about Nov 9.** | none | You | The artifact file is in the workspace and its SHA-256 is recorded in the work log |
| T0.2 | Review and merge the status and roadmap branch `docs/project-status-and-roadmap-20261103` (open a PR if none exists) | none | You (Claude reviews the diff) | `PROJECT_STATUS.md` and `ROADMAP.md` are on `main` |
| T0.3 | Prepare the EXP-030 archive. Claude checks the artifact against what `EXP-030.sh` should produce and checks `scripts/archive_experiment.py`. Because the tool verifies VPS-only inputs, the final archive step may have to run on the VPS with a command Claude supplies | T0.1 | Claude prepares; you run the VPS step if needed | `research-archive/EXP-030/ARCHIVE_MANIFEST.json` hashes match the artifact, in a PR on `archive/EXP-030-r02`. You merge it |
| T0.4 | Record your answers to D1–D12 and S-2 in section 11 of this file (a PR to this file) | none | You | Answers are written down |
| T0.5 | Re-run the Jangus test suite and the local-model benchmark on your PC. This is preparation only; it does not authorize J1 or J2 | none | You | The test counts and the benchmark JSON are sent back. The JSON is kept outside every checkout |
| T0.6 | Run `pytest -q` in a clean Windows virtualenv on trade-alerts `main` | none | You | Pass/fail counts reported. Failures are investigated, never weakened |

### Phase T1: Read-only interface in trade-alerts

Goal: `scripts/agent_api.py` answers read-only questions as JSON. It writes no files, uses no network and does not import the backtest runners.

Branch pattern: `feature/agent-api-<step>`, one pull request per step.

| ID | Task | Depends on | Owner | Done when |
| --- | --- | --- | --- | --- |
| T1.1 | Write the contract `docs/agent_api.md`: each command's output shape, exit codes, the response envelope (`schema_version`, repo SHA, payload SHA-256, `truncated`), the 64 KB cap, and errors as JSON | T0.2 | Claude drafts; you approve (G1) | You approve the contract in the PR. No code yet |
| T1.2 | Skeleton CLI `scripts/agent_api.py`: argument parsing, envelope, cap, JSON error objects, distinct exit codes, never a traceback | T1.1 | Claude | `tests/test_agent_api.py` checks valid JSON, `schema_version`, the cap sets `truncated`, an unknown command returns a non-zero exit with a JSON error |
| T1.3 | `status`: HEAD SHA, branch, clean-tree flag, contents of `run-requests/current.json` | T1.2 | Claude | Test: output matches `git` on a fixture repo, and `git status --porcelain` is identical before and after the command |
| T1.4 | `policy`: parse `config/research_policy.yaml` | T1.2 | Claude | Test on a fixture and on the real file (periods listed; holdout reported as `not_established`) |
| T1.5 | `experiments`: list each archive directory with its manifest hash and file count. **First inspect the real `ARCHIVE_MANIFEST.json` format** and record it in the PR. Directories without a manifest (for example `EXP-030-PREPARATION`, `README.md`) are reported, not crashed on | T1.2 | Claude | Test on a fixture archive, plus a run on the real `research-archive/` with the count matching the 27 manifests |
| T1.6 | `results <EXP>`: read the metrics files for one experiment and check each SHA-256 against its manifest. Refuse unknown IDs and any path containing `..` or a separator | T1.5 | Claude | Test: a tampered fixture file reports a mismatch; `../` is refused; output is capped |
| T1.7 | `findings`: list finding IDs and status from `trade-brain/40-Research/Findings/FINDINGS-INDEX.md`. **Check that file exists and its format first**; stop and report if it does not | T1.2 | Claude | Test on the real index and a fixture |
| T1.8 | `roadmap`: current next action and unchecked items from `phases.md` (available now). Add `ROADMAP.md` once T0.2 is merged | T1.2 | Claude | Test: unchecked items match the file |
| T1.9 | `coverage`: per-year contract segments and warm-up row counts from `docs/research/r7_control_coverage.json` and `research-archive/EXP-INTEGRITY-HISTORY-INVENTORY/`. Every output is labelled "coverage uncertified" | T1.5 | Claude | Test: the label is always present; a fixture matches the source numbers exactly |
| T1.10 | `compare <A> <B>`: metric differences, or `not_comparable` when result shapes differ | T1.6 | Claude | Test: identical inputs give zero deltas; different shapes give `not_comparable` |
| T1.11 | Cross-command guard: every command leaves the working tree byte-identical; a full `pytest -q` passes | T1.3–T1.10 | Claude | The full suite is run and the exact counts are logged. Nothing is claimed without that log |
| T1.12 | Open the T1 pull request, summarising the files and test results | T1.11 | Claude | PR opened. You merge (G1) |

### Phase T2: Safety hardening in trade-alerts

Goal: nothing an agent can reach can start or alter a VPS run without your merge.

| ID | Task | Depends on | Owner | Done when |
| --- | --- | --- | --- | --- |
| T2.1 | `.github/workflows/tests.yml`: full `pytest` on every push and pull request, and nightly at 02:17 Toronto time (`17 7 * * *` UTC). It never touches the VPS | T1 merged | Claude | A test pull request shows a green `pytest` check. A nightly run appears the next morning |
| T2.2 | `scripts/ci/check_agent_paths.py` with tests. Blocks agent branches from touching forbidden paths (see section 6) | T2.1 | Claude | Tests: an `agent/*` branch touching `.github/` fails; a documentation-only change passes |
| T2.3 | Pinned VPS host key: the workflow reads `TRADE_VPS_KNOWN_HOSTS` and connects with `StrictHostKeyChecking=yes` instead of `ssh-keyscan` | T2.1 | You add the secret (from the VPS console fingerprint); Claude edits the workflow | Workflow lint passes. **The real connection is only tested at your next explicit run**, and this plan does not trigger one |
| T2.4 | Branch protection on `main`: pull request and passing `pytest` required | T2.1 | You (GitHub settings) | A direct push to `main` is rejected; a red PR cannot merge |
| T2.5 | Draft a forced-command script for the VPS key. It accepts only `EXP-NNN`, a safe request ID and a 40-character commit | T2.3 | Claude drafts; you decide whether to install it | The draft is reviewed. Nothing is installed by an agent |
| T2.6 | Gate G2 review | T2.1–T2.5 | You | Merged |

### Phase J1: Jangus slice A (needs your written "go", G3)

Goal: the smallest Jangus work that runs a read-only report with zero model calls. Built in the Jangus repo, one task per pull request on `phase-2/<topic>` branches.

Acceptance for the whole slice: the existing 239 Jangus tests still pass; the new tests pass on Ubuntu and Windows CI; `ruff` and strict `mypy` on the kernel are clean.

| ID | Task | Depends on | Owner | Done when |
| --- | --- | --- | --- | --- |
| J1.0 | Record the slice A authorization in Jangus `MEMORY.md` | G3 | You | Written in the file |
| J1.1 | ADR `docs/decisions/002-trade-research-domain.md`, and the PRD decision-log amendment (D2) | J1.0 | Claude | Reviewed and merged |
| J1.2 | Add tasks N1–N7 and 16a to `.taskmaster/tasks/tasks.json`. Never edit finished tasks | J1.1 | Claude | Validates; merged |
| J1.3 | Config keys: `host` (parking-lot item) and the trade-alerts clone path | J1.2 | Claude | Config tests pass; loader rejects a `localhost` model URL |
| J1.4 | Read-only tool pack `src/jangus/tools/trade_research/`: `trade.sync`, `trade.status`, `trade.roadmap`, `trade.experiments`, `trade.coverage`, `trade.results`, `trade.compare`, `trade.policy`. Each is a strict argument model, tier T1, with `verify` and `reconcile`, and wraps one `agent_api` command with fixed arguments and no shell | J1.3 and T1 merged | Claude | Tests against a **fake** `agent_api` and a fixture repo. Rejects unknown tools, extra arguments, paths outside the clone, and shell characters |
| J1.5 | `trade.tests`: runs `pytest` only on a clean checkout of `main` at a known SHA, in its own venv, with no secrets in the environment, a time limit and capped output | J1.4 | Claude | Tests pass with a fake runner. Real execution on the PC only after you approve it (the Setup Guide's Part 4 treats this as a risk; see section 3) |
| J1.6 | Kernel-run directive runner (task 16a): runs `runner: kernel` tasks with fixed tool steps, zero model calls, and sets status only from verified evidence | J1.4 | Claude | A kernel-only directive completes. A failing step marks its task `deferred`, halts the directive and alerts |
| J1.7 | CLI `jangus run <directive>` and `jangus status` (N3) | J1.6 | Claude | CLI tests pass |
| J1.8 | Kernel-written report template for trade directives (N4). No model writes it | J1.6 | Claude | Two runs at the same commit produce identical reports |
| J1.9 | Optional `keyring` extra (N6), and a first real test of the Windows Credential Manager backend | J1.7 | You run the Windows check; Claude writes the extra | Check reported back |
| J1.10 | Evidence review in the style of `docs/reviews/PHASE_1.md` | J1.1–J1.9 | Claude writes; you accept | You accept |

### Milestone 1a: zero-model report

| ID | Task | Depends on | Owner | Done when |
| --- | --- | --- | --- | --- |
| M1a.1 | Approve the draft spec `trade-research-reader.yaml` (`max_tier: T1`, no escalation model). Its hash is shown by `jangus spec show` | J1.10 | You | `jangus spec approve` run by you |
| M1a.2 | Issue the directive `dir-trade-readonly-report-001` (three kernel tasks, task 4 omitted). Run it | M1a.1 | You run; Claude reads the output | A report is written |
| M1a.3 | Acceptance: two runs at the same commit give identical reports; the ledger shows zero model calls; the clone is unchanged apart from `git fetch`; killing the process mid-run and restarting reconciles without repeating an effect; scenarios T01–T06 and T08–T10 in section 7 pass | M1a.2 | Claude records results; you verify | Results logged |
| M1a.4 | You read three reports and decide whether to continue (G4) | M1a.3 | You | Written decision |

### Phase J2: Jangus slice B (needs your written "go", G5)

Goal: add the model path, with cost control built first.

| ID | Task | Depends on | Owner | Done when |
| --- | --- | --- | --- | --- |
| J2.1 | Durable budgets and spend cap (task 14) | G5 | Claude | Budgets survive a restart |
| J2.2 | Run loop with proposals, including a `task.answer` tool with a strict schema (task 15) | J2.1 | Claude | Fake transport tests pass |
| J2.3 | Model tasks in the directive runner, expanded into subtasks first (task 16) | J2.2 | Claude | Expanded subtasks are listed in the PR before work starts |
| J2.4 | Attempt policy: repeat detection, per-task limits, escalation ladder (task 26) | J2.2 | Claude | A third failed attempt stops the task and alerts |
| J2.5 | Metering per call (task 25) and pre-call budget gate (task 28) | J2.1 | Claude | A call that would exceed a budget stops before it is made |
| J2.6 | Scenarios B08–B12, B24–B26, B29–B34, B36–B41 from Jangus `docs/PHASES.md` (**not re-read for this plan**; confirm names first) | J2.1–J2.5 | Claude; you accept | Pass recorded |
| J2.7 | Only if you choose a Claude step-up: create a dedicated API key with a provider spend limit, store it in Credential Manager, set `claude_enabled = true` | D10 | You | Stored; never placed in a file, prompt or chat |

### Milestone 1b: one model task

| ID | Task | Depends on | Owner | Done when |
| --- | --- | --- | --- | --- |
| M1b.1 | Task 4 of the directive: propose the next research task. The answer is a `task.answer` object with an `item_id` and short `reason`; the kernel rejects any `item_id` not in the `trade.roadmap` output | J2.6 | Claude | Rejection of an invented item is tested |
| M1b.2 | Seven consecutive days of scheduled `jangus run` (Windows Task Scheduler), with zero manual fixes | M1b.1 | You | Ledger shows: zero Claude calls; tokens within 20,000; zero write attempts; no unexplained entries |
| M1b.3 | Sign-off (G6) | M1b.2 | You | Written |

### Later milestones (each needs G7)

**M2: Notes and hypotheses (draft pull requests only)**

| ID | Task | Depends on | Done when |
| --- | --- | --- | --- |
| M2.1 | Token with access to `jenozu/trade-alerts` only, stored in Credential Manager. Branch protection from T2.4 must already be on | G2 | Token stored; you confirm it cannot push to `main` |
| M2.2 | Tools `trade.write_note` (T2, `trade-brain/00-Inbox/` on an `agent/*` branch) and `trade.open_draft_pr` | M2.1 | Tests: writes only to allowed paths; the PR is a draft; the head SHA matches |
| M2.3 | Every number in a note must appear in a tool result (kernel-checked) | M2.2 | A note with an invented number is rejected |

**M3: Prepare experiments (no run)**

Blocked until the data gate is closed and S-1, S-2 and S-3 are answered.

| ID | Task | Depends on | Done when |
| --- | --- | --- | --- |
| M3.1 | Data gate closed: Barchart repairs done and segments rebuilt as new versions (see data track DT below) | DT.3 | `coverage` shows usable warm-up on every segment used |
| M3.2 | Sweep runner in trade-alerts (`automation/sweeps/` and a wrapper): reads a committed grid, refuses grids above `max_variants`, refuses any date in the holdout | M3.1, S-4 | A 4-variant fixture sweep produces 4 archived runs and one report; an oversize grid is refused |
| M3.3 | `trade.edit_branch` (T2): writes only on `agent/*`, with a path allowlist; refuses `main`, `research-archive/`, `RULES.md` and the research policy; per-experiment lease check | M2.2 | Tests cover each refusal |
| M3.4 | Experiment builder: one factor changed, frozen control, preregistration written before the run, CI green, **no run** | M3.2, M3.3 | Diff touches exactly the named factor; `config/strategy.yaml` defaults unchanged |

**M4: Run requests and archiving**

| ID | Task | Depends on | Done when |
| --- | --- | --- | --- |
| M4.1 | Approval commands `jangus approvals list / approve / reject` (pulled forward from task 22) | J2 | Shows the exact payload hash being approved |
| M4.2 | `trade.request_run` (T3): preflight in the kernel (wrapper exists on `main`; request ID never used; no run in progress; inside research window). Opens a pull request that changes only `run-requests/current.json` | M4.1, D4, D9 | Duplicate request IDs refused; a crash after approval reconciles |
| M4.3 | VPS-side archive step and a workflow that opens an archive pull request from the run record | D5, T0.3 | The first real run goes from approval to archive pull request with no manual copying |
| M4.4 | Expiry watcher: run records older than 20 days with no archive pull request raise an alert | M4.3 | Alert fires in a test |

**M5: Schedule and coordinator**

| ID | Task | Depends on | Done when |
| --- | --- | --- | --- |
| M5.1 | `jangus tick` (task 19), watchers (new commit, new run record, expiring record), kernel-written daily and weekly reports | M4 | Jangus's own phase 3 gate passes |
| M5.2 | Jangus orchestrator as Research Coordinator (task 22), with directive templates | M5.1 | Only agents whose specs you approved can start; the daily escalation cap holds |

---

### Data-integrity track (parallel, trade-alerts)

These items are not in the Setup Guide's build sequence, but the Autonomous guide puts them first. They gate M3.

| ID | Task | Owner | Done when |
| --- | --- | --- | --- |
| DT.1 | Report Barchart repair status from your PC (what is downloaded, what is not) | You | Status sent |
| DT.2 | Read-only `data-check` (`automation/checks/data-check.sh`, `data-check.yml`) on the VPS. Recorded in `REPOSITORY_STATE.md` as a check, not an experiment | Claude drafts; you approve | Report shows first/last timestamp, usable days, bars, gaps, rollovers |
| DT.3 | Finish repairs and rebuild the contract segments as new versions (see `PROJECT_STATUS.md`) | You (downloads); Claude (rebuild code) | Each segment shows warm-up history; coverage is certified by the check, not claimed |
| DT.4 | Decide on the zero-trade baseline (S-1) before any optimization | You | Written decision |

---

## 6. Path guard (applies from T2.2 onward)

| Branch pattern | May touch | Must never touch |
| --- | --- | --- |
| `agent/*` (notes, experiment preparation) | `trade-brain/`, `docs/research/`, new files under `automation/experiments/`, `tests/`, and `src/` or `config/` files named in the preregistration | `.github/`, `scripts/automation/`, `run-requests/`, `RULES.md`, `config/research_policy.yaml`, existing wrappers, anything under `research-archive/` |
| `agent-run/*` (run requests) | `run-requests/current.json` only | Everything else |
| `archive/*` (evidence) | New directories under `research-archive/` only | Existing archive files (immutable) |

---

## 7. Acceptance scenarios for Jangus `docs/MVP.md` (proposed)

| ID | Scenario |
| --- | --- |
| T01 | Only allowlisted `agent_api` and `pytest` commands run, with fixed arguments; shell characters are rejected |
| T02 | A T2 or T3 proposal from the read-only agent is rejected, and the clone is unchanged afterwards |
| T03 | A path outside the clone, or a symlink out of it, is rejected |
| T04 | Every tool response is parsed, hashed and logged; invalid JSON fails the task instead of being guessed at |
| T05 | Every number in the report traces to a ledger hash |
| T06 | A result file or note containing instruction-like text ("ignore your rules…") is treated as data and causes no proposal |
| T07 | A proposed next task must be an item in the roadmap output |
| T08 | Two runs at the same commit give identical reports |
| T09 | Milestone 1a records zero model calls; 1b stays inside its budget with zero Claude calls |
| T10 | Killing the process mid-run and restarting reconciles without repeating an effect |

---

## 8. Dependency summary

```
T0.2 ──► T1.1 (G1) ──► T1.2 ──► T1.3…T1.10 ──► T1.11 ──► merge T1
                                                          │
                                  T2.1 ──► T2.2, T2.3, T2.4 ──► G2
                                                          │
            G3 (your go) ──► J1.0 ──► J1.1 ──► J1.2 ──► J1.3 ──► J1.4 ──► J1.5…J1.9 ──► J1.10
                                                                                        │
                                              M1a.1 ──► M1a.2 ──► M1a.3 ──► G4
                                                                       │
                                  G5 (your go) ──► J2.1…J2.5 ──► J2.6 ──► M1b.1 ──► M1b.2 (7 days) ──► G6
                                                                                                    │
                                         M2 (G7) ──► M3 (needs DT.3, S-1..S-4) ──► M4 (D4, D5, D9) ──► M5
```

T0.1 is independent and is the only item with a hard date (about Nov 9).

---

## 9. Work log

Append one line per completed task: date, task ID, PR link, test command and exact result, and any decision made. Empty until work starts.

| Date | Task | PR | Test run and exact result | Notes |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

---

## 10. Parking lot (ideas not in this plan)

- Adopt the real Task Master tool, or convert this file to `.taskmaster/tasks/tasks.json`. Not needed for the first milestones.
- Run Jangus on the VPS (Jangus Phase 7). Needs its own decision record.
- Move the VPS to a non-root account. Involves moving data paths; a later decision.
- Bump GitHub Actions to current versions (Node 20 deprecation warning; `ubuntu-latest` changed on Oct 19).
- Correct stale docs: `phases.md` and `REPOSITORY_STATE.md` still say EXP-030 has not run.
- A `not before` field for Jangus directives (the research window).
- Result cache (Jangus task 29), recipes (task 30), watchers beyond the three in M5 (task 31), cost reports (task 33).

---

## 11. Decision record

Fill in as decisions are made. Do not edit a line once it is recorded; add a new line instead.

| Date | ID | Decision | Decided by |
| --- | --- | --- | --- |
| — | — | — | — |

---

## 12. Change log for this plan

| Date | Version | Change |
| --- | --- | --- |
| 2026-11-03 | 0.1 | Created from the Setup Guide (Nov 3 2026). No task started. |
