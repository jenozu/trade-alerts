# PROJECT_STATUS — trade-alerts audit

**Audit date:** 2026-11-02
**Audited commit:** `main` @ `cd8e431` (2026-10-12, "Accept observed hyphenated minute timestamps in Barchart downloads (#19)")
**Auditor:** Claude, read-only audit from a fresh clone. Nothing was pushed, no experiment was run, and the VPS was not contacted.

This file is a **point-in-time audit**. It does not replace the project's existing
source-of-truth files. Per `REPOSITORY_STATE.md`, that order stays:
`main` → reviewed PRs → `phases.md` → `refine-roadmap.md` → `research-archive/`.

## How to read the evidence labels

| Label | Meaning |
|---|---|
| **VERIFIED** | I checked it myself in this audit (ran it, read the code, or read the archived evidence file). |
| **REPORTED** | The repository's own docs say so; I did not or could not re-check it (usually because the evidence lives on the VPS or your Windows PC). |
| **INFERRED** | My interpretation of verified evidence. Treat it as a lead to confirm, not a fact. |
| **UNKNOWN** | Nobody can tell from the repository alone. |

---

## 1. Summary

The project is much further along than "build a backtester". It already has a
causal (no-look-ahead) feature engine, a contract-isolated backtest path, 867
passing tests, more than 30 archived experiments, a three-way development/
validation/holdout data policy, and a working GitHub Actions → VPS execution path.

Two problems block meaningful research right now:

1. **Data acceptance gate is open.** Most quarterly contract segments start
   evaluating trades on their very first bar with zero warm-up history (see §6).
   Repair downloads from Barchart were in progress on your Windows PC when work
   stopped on 2026-10-12. The status of those downloads is UNKNOWN.
2. **The corrected strategy path produces zero trades.** In 2023, 2024 and 2025
   the integrity-corrected strategy found 16 eligible signals in total and accepted
   **0** trade plans. There is no trade-producing baseline to optimize against yet.

There is also one **time-sensitive item**. The only copy of the EXP-030 run record
visible from GitHub is an Actions artifact. Actions keeps artifacts for 30 days, so
it should expire around **2026-11-09**, and it has not been archived into the repository.

---

## 2. What currently works

| Item | Status | Evidence |
|---|---|---|
| Full test suite | **VERIFIED**: 867 passed, 968 warnings, 47.6 s, Python 3.13, clean working tree afterwards | Ran `pytest -q` in an isolated venv |
| Causal feature modules (swings, liquidity, FVG/IFVG, structure BOS/MSS/CHoCH, displacement, VWAP, RVOL, sessions, premium/discount, DOL, HTF bias, scorer) | **VERIFIED** present, covered by append-invariance / "future bars do not rewrite past" tests | `src/`, `tests/test_structure.py`, `test_volume.py`, `test_resample_timeframe_visibility.py`, etc. |
| Sweep vs valid break distinction | **VERIFIED** in code: `structure_state` separates wick sweep, body-close break and strong displacement break | `docs/strategy_fidelity_audit.md`, `src/structure_state.py` |
| Contract-isolated feature builds (no state leaks across contracts) | **REPORTED** complete for 2023/2024/2025 | `docs/integrity_closeout_20261009.md` |
| Continuous MNQ 1-minute dataset 2021-12-20 → 2026-09-04 | **REPORTED** certified: 19 contracts, 18 rollovers, 1,663,671 rows, 0 duplicates, 0 nulls, **no price adjustment** | `docs/BARCHART_HISTORY_WORKFLOW.md` (data itself is VPS-only, not in Git) |
| Rollover rule | **REPORTED**: roll at the CME session open before the first day the new contract has higher volume for two consecutive days; all 18 rolls confirmed, none fell back to a default | same |
| Immutable experiment archive with SHA-256 manifests | **VERIFIED** convention + tooling (`scripts/archive_experiment.py`, `research-archive/*/ARCHIVE_MANIFEST.json`, 328 files) | |
| Experiment input/output locks | **VERIFIED** tooling exists (`scripts/lock_experiment_inputs.py`, `src/experiment_identity.py`) | |
| Development / validation / holdout policy | **VERIFIED**: 2023–2025 = development data; 2026 = pseudo-out-of-sample; no untouched holdout yet | `config/research_policy.yaml`, `docs/research_dataset_policy.md` |
| GitHub Actions → VPS over SSH | **VERIFIED from public Actions page**: run #1 failed (11 s, the SSH auth blocker); run #2 **succeeded** on 2026-10-10 (2 min 8 s) | `run-trade-experiment.yml` runs 38061224851 / 38062346882 |
| Explicit-run safety | **VERIFIED** in code: only a push to `main` that *changes* `run-requests/current.json` triggers; ordinary pushes do not | `.github/workflows/run-trade-experiment.yml` |
| Command allowlist | **VERIFIED**: the request names an experiment ID only; the VPS runs only `automation/experiments/EXP-NNN.sh`; no arbitrary shell | `scripts/automation/parse_run_request.py`, `execute_run_request.py` |
| VPS run guards | **VERIFIED** in code: must be on `main`, clean tree, fast-forward only, exact SHA match, venv present, full `pytest` preflight before the wrapper, duplicate request IDs refused (`mkdir(exist_ok=False)`), per-run `manifest.json` | `execute_run_request.py`, workflow |
| Concurrency + timeout | **VERIFIED**: single concurrency group, no cancel-in-progress, 360-minute job timeout | workflow |
| Batch shorthand parser | **VERIFIED**: parses `run 31-35` etc. (max 20 IDs) but **never executes** anything | `scripts/automation/parse_batch_command.py`, tests |
| Barchart repair downloader (Windows, Playwright) | **VERIFIED** code + CI (8 workflow runs, latest green 2026-10-12); fail-closed, never overwrites, append-only progress log | `tools/barchart/download_history_repairs.py`, `docs/barchart_history_repairs.md` |
| Research knowledge base | **VERIFIED**: 18 experiment notes, 27 findings (F001–F029) | `trade-brain/40-Research/` |

## 3. What has already been completed (do not redo)

**REPORTED** in `phases.md` / `refine-roadmap.md`, archived in `research-archive/`:

- EXP-001 to EXP-021 (EXP-012 order blocks is **blocked**): score bands, long vs short, setup family, year/regime, levels, HTF bias, sweep, breakout acceptance, displacement, structure, FVG, premium/discount, DOL, RVOL, SNR, VWAP, S/R confluence, room-to-target, time of day, execution confirmation.
- R1 baseline decomposition, R2 component ablation, R4 scoring/threshold sweep.
- R5 stop-loss research (FIXED_15 and ATR_1.0 kept as *validation candidates only*).
- R6 fixed-target / partial-exit research (TP100 stays the control).
- R7.0 continuation-displacement: completed and **rejected**. Do not rerun.
- Pre-critical integrity checkpoint (PR #7): commission/net accounting, execution invariants, dataset classification, immutable input identities, strategy-fidelity audit, 2023–2025 diagnostics.
- Read-only contract history inventory (archived `EXP-INTEGRITY-HISTORY-INVENTORY`).
- Research-only `confirmation_first_family_v1` option (approved by you, implemented, tested).

**Important caveat (REPORTED, `docs/strategy_fidelity_audit.md`):** EXP-001 to EXP-021 and R4–R6 used the older `score_signal_v1` model. It enters at market on the next bar after a scored signal, and its "continuation" label is applied after the fact. They remain valid records of what was tested, but they **do not** describe your intended retest-based strategy and do not certify the corrected execution contract.

## 4. Current experiment status

| Experiment | Status | Evidence |
|---|---|---|
| EXP-001 | Complete (historical `score_signal_v1` semantics); wrapper exists | `research-archive/EXP-001`, `automation/experiments/EXP-001.sh` |
| EXP-002 … EXP-021 | Complete (same caveat); EXP-012 blocked | `research-archive/` |
| EXP-022 … EXP-029 | Deliberately unassigned | registry |
| **EXP-030** | **Ran successfully on the VPS 2026-10-10 (r02). NOT archived, NOT reviewed.** Reported outcome: 8 eligible signals (7 + 1 added continuation), **0 accepted plans, 0 trades** | Actions run 38062346882; artifact `EXP-030-r02-20261010-run-record` (32.3 KB); `docs/research/proposed_experiment_registry_r7_r12.md` (REPORTED) |
| EXP-031 … EXP-050 | **Proposed only.** Draft specs sit in 4 open PRs (#10–#13); 0 executable or approved | GitHub PR list (4 open, 15 closed) |

**Stale docs (VERIFIED):** `phases.md` line 1142, `REPOSITORY_STATE.md` and
`trade-brain/40-Research/Research-Index.md` still describe EXP-030 as "not executed" and the run request as "idle".
`run-requests/current.json` actually contains the completed `EXP-030-r02-20261010` request.
Only the proposed-registry doc reflects the successful run.

## 5. What is partially implemented

- **Execution realism.** Slippage is configured (0.25 pt entry and exit). Commissions are **disabled** (`commission.enabled: false`) and the diagnostics use quantity 1. Your actual MNQ fees are not documented. Limit/retest fills, stop/breakout fills and session liquidation are **not certified** (REPORTED, integrity closeout).
- **Intrabar ambiguity.** `same_bar_stop_and_target_behavior: stop_first` is conservative (VERIFIED in config). Multiple chronology events can still complete on the **same 1-minute bar**, which OHLC cannot order. An audit test documents this (REPORTED).
- **Setup families.** Sweep reversal and break/retest continuation exist as execution families. **VWAP/cloud reaction and opening-range/opening-drive are context only**, not independent entry families. IFVG-only entries are not implemented. Order blocks are blocked (EXP-012) (REPORTED, fidelity audit).
- **DOL targeting.** The baseline records DOL direction but targets fixed price distances, not the liquidity pool (REPORTED).
- **Batch / queue.** The parser exists, but there is no durable multi-experiment queue. Each run is one manual request commit (VERIFIED).
- **Walk-forward / holdout.** The policy is written, but no walk-forward runner exists. The holdout is `not_established` (VERIFIED).
- **Live/production side.** Systemd timers for premarket, live, recap and health exist (`deploy/systemd/`), plus Telegram transport. This is alert-only, with no brokerage (VERIFIED, no order code). Shadow mode was never completed (REPORTED, phases.md).

## 6. Current data coverage

Raw data is on the VPS and your Windows PC, not in Git. I could not open it.
What follows comes from the archived inventory JSON (VERIFIED as an archived file;
the underlying data itself is REPORTED).

| Item | Value |
|---|---|
| Instrument | MNQ (Barchart symbol `NM`), 1-minute, unadjusted prices |
| Earliest / latest (continuous series) | 2021-12-20 06:00 UTC → 2026-09-04 20:59 UTC (REPORTED) |
| Total bars (continuous) | 1,663,671 (REPORTED) |
| Contracts | 19 quarterly contracts (exact list in VPS-only `data/raw/barchart/rollover_analysis.json`; the archived inventory covers NMZ22 → NMH26) (REPORTED) |
| Rollovers | 18, all by confirmed volume crossover (REPORTED) |
| Yearly corrected builds | 2023: 440,032 rows · 2024: 441,600 · 2025: 441,015 (incl. context) (REPORTED) |
| Usable trading days | **UNKNOWN**: never computed against an exchange calendar |
| Exchange holiday / session completeness | **Not certified** (inventory limitation #1) |
| Data after 2026-09-04 | Not acquired |

**Warm-up gap (VERIFIED from `research-archive/EXP-INTEGRITY-HISTORY-INVENTORY/CONTRACT_HISTORY_INVENTORY.json`):**

| Year | Segments that start evaluating on bar 1 with **0 context rows** |
|---|---|
| 2023 | NMM23 (from 2023-03-13), NMU23 (06-12), NMZ23 (09-11), NMH24 (12-11) |
| 2024 | NMM24 (03-11), NMU24 (06-17), NMZ24 (09-16), NMH25 (12-16) |
| 2025 | NMM25 (03-17), NMU25 (06-16), NMZ25 (09-15), NMH26 (12-15) |

Only the first segment of each year has warm-up context (~13–18k rows).

**INFERRED impact:** the strategy config needs 20 previous sessions for relative
volume and builds multi-day HTF swings, FVG and structure state. For roughly the
first several weeks after every quarterly roll (about 4 of each year's 5 segments),
those features are missing or immature. This could suppress signals and may
contribute to the near-zero signal counts. That is not yet proven.

**Possible roll-weekend hole (INFERRED, needs VPS check):** for the 7 contracts with
"no earlier history" (NMM23, NMU23, NMZ23, NMM24, NMU24, NMZ24, NMU25), the new
contract's file starts Monday 05:00 UTC (00:00 CT), and the prior contract ends
on Friday. The roll weekend's Sunday-evening Globex session (~17:00–24:00 CT)
therefore seems absent from the isolated build. This would affect overnight/Asia
levels on those Mondays, not RTH bars directly.

The **remaining inventory step** (REPORTED) is to locate the original CSVs and
normalized chunks, then classify sessions against the exchange schedule. The
repair downloader requests 56 calendar days before each roll for 13 incoming
contracts. Whether you completed those downloads is **UNKNOWN**.

## 7. Current automation status

| Step in your desired workflow | Status |
|---|---|
| 1. Prepare experiment | Manual (agent writes wrapper + tests) |
| 2. Review changes | Manual (PR) |
| 3. Push to GitHub | Manual |
| 4. Explicitly request execution | Manual: edit `run-requests/current.json` and push to `main` (by design) |
| 5. Actions → VPS over SSH | **Automated and working** (run #2 green) |
| 6. VPS runs operation | **Automated**, with preflight tests and guards |
| 7. Results/logs returned and stored | **Half-automated.** Small run record is uploaded as an Actions artifact (30-day retention). Copying evidence into `research-archive/` and committing it is **manual**, and this is where EXP-030 stalled |

Still manual or missing:
- Barchart downloads (Windows PC, interactive login; must stay manual for login/CAPTCHA).
- VPS-side diagnostic exports, which you have been pasting back into chats.
- Archiving run records into Git.
- `workflow_dispatch`, scheduled jobs, retries, notifications, a run queue, `status`/`logs` commands that read Actions.
- Host-key pinning: the workflow runs `ssh-keyscan` on every run, which trusts whatever host answers. A pinned `known_hosts` secret would be safer.
- Maintenance: Actions annotations warn that Node 20 actions are deprecated, and `ubuntu-latest` moved to Ubuntu 26 on 2026-10-19 (not yet exercised by a run).

## 8. What is broken

Nothing in the code is demonstrably broken. Tests are green and the last VPS run succeeded. These are defects in **state**:

- EXP-030 evidence is not archived, and its artifact is about to expire.
- Canonical docs (`phases.md`, `REPOSITORY_STATE.md`, Research-Index) contradict the Actions history about EXP-030 and SSH readiness.
- 968 test warnings, mostly NumPy "generic timedelta unit is deprecated, and will raise an error in the future". A future NumPy upgrade will turn these into failures. `requirements.txt` allows `numpy<3`.

## 9. What is missing

- A **trade-producing, trustworthy baseline** under the corrected execution contract.
- Certified data coverage: warm-up sufficiency, exchange-session classification, a usable-trading-days count.
- Documented account-specific commissions/fees.
- Walk-forward runner, untouched holdout, parameter-sensitivity tooling.
- Configuration-driven parameter sweeps ("500 variations") with ranked reports. Today each experiment is a bespoke `run_expNNN_*.py` script.
- Standard per-run report with equity/drawdown curves (metrics exist piecemeal across research modules).
- Research agent / journal automation (the `trade-brain/` structure is a good manual foundation).
- Dashboard (correctly deprioritized).
- The original strategy source documents (NotebookLM framework, alert JSON) referenced by the fidelity audit are not in this session. I relied on `config/strategy.yaml`, `docs/strategy_fidelity_audit.md` and `docs/context_bias_confirmation_principles.md`.

## 10. Current blockers

| # | Blocker | Who can unblock |
|---|---|---|
| B1 | EXP-030 run record artifact expires ~2026-11-09 | **You.** Download it while signed in to GitHub (I can't; artifact downloads need auth) |
| B2 | Status of Barchart repair downloads unknown | **You.** Report what `download_history_repairs.py status` shows on your PC |
| B3 | Data acceptance gate (warm-up, sessions) not closed | Engineering, after B2 |
| B4 | Zero accepted trades on corrected control | A **strategy decision** by you, informed by B3. Not something an agent may "fix" by loosening rules (RULES.md §6) |
| B5 | This session has **read-only** access; push access was declined | You. Grant push access, or commit these files yourself |

## 11. Conflicts between the new master prompt and existing project rules

These need your decision. I have **not** changed anything to resolve them.

1. **`workflow_dispatch`.** The new prompt asks for it. `CHATGPT_COMMANDS.md` says "Do not use `workflow_dispatch` as a shortcut", and the existing trigger is a reviewed commit to `run-requests/current.json`. Recommendation: keep the commit-based trigger. It leaves an auditable Git record of every authorization.
2. **"batch 100" meaning.** The new prompt means *100 parameter variations of one experiment*. Existing `batch` means *up to 20 separate experiment IDs*. Recommendation: name the new one something like `sweep <EXP> <grid>` to avoid confusion.
3. **Results location.** The new prompt suggests `data/results/research_runs/<timestamp>_<id>/`. The project already uses gitignored working outputs plus committed `research-archive/EXP-NNN/` with hash manifests, and `data/results/research_runs/` is already used by EXP-001. Recommendation: keep both layers as they are.
4. **`ROADMAP.md` vs `phases.md`.** Voyages reads `phases.md`. A second roadmap risks drift, which is exactly what `REPOSITORY_STATE.md` warns about. I wrote `ROADMAP.md` as a short **priority view that defers to `phases.md`**.
5. **Unmerged `feature/tradingview-pinescript` branch.** It contains a "backtesting-to-bot roadmap with gated research and paper trading" and its own CI workflow (4 failed and 2 passed runs on 2026-10-11). The new prompt forbids brokerage connection. Decide whether that branch's roadmap is still wanted.
6. **Stale branches.** There are 33 remote branches, including `perf/scoring-streaming-memory` with two unique, unreviewed commits. Do not delete any without the review that `REPOSITORY_STATE.md` requires.

## 12. Next five recommended tasks

1. **Save EXP-030 evidence (urgent, ~10 minutes of your time).** Download the run-record artifact from run 38062346882, then archive it to `research-archive/EXP-030/` with `scripts/archive_experiment.py`, review it, and correct the stale docs.
2. **Close the data acceptance gate.** Finish/verify the Barchart repair downloads. Then, using new versioned artifacts only, rebuild contract segments with real pre-roll history. Classify sessions against the CME calendar, publish a coverage report (§6 fields plus usable days), and confirm or refute the roll-weekend hole.
3. **Decide whether to re-run the corrected 2023–2025 diagnostics on the repaired data** and see whether signal counts and accepted plans change. Keep the old results.
4. **Strategy decision on the zero-trade control.** Review *why* the 16 signals were rejected (13 structural risk, 14 first-obstacle room, 13 TP1 asymmetry). Decide whether those rules represent your actual trading, or need a versioned, preregistered change. Then freeze a baseline.
5. **Automation hardening.** Auto-archive run records back into the repo via a PR, pin the VPS host key, update the deprecated actions, add read-only `status`/`logs` helpers. Then build a config-driven sweep runner on top of the frozen baseline.

## 13. Single most important next task

**Close the data acceptance gate (task 2), right after the 10-minute EXP-030 save (task 1).**

Why: archived evidence shows that about 4 of every 5 contract segments start with
no warm-up history. Every downstream result (signal counts, the zero-trade
control, any future optimization) depends on features that may be immature
for weeks after each roll. Optimizing now would automate conclusions drawn from
data we already know is incomplete. That matches your own stated priority order.
