# MNQ strategy MVP — backtesting to paper trading to an eventual bot

**Branch:** `feature/tradingview-pinescript` — this is the **ONLY write target for this MVP track**.
**Repository:** `jenozu/trade-alerts`.
**Owner decision:** Preserve `main` as-is; do **not** push to, merge into, open a PR targeting, or deploy changes from this MVP track to `main`.
**Last reviewed:** 2026-10-11.
**Status:** **Stage 1 — historical-data acceptance**. No strategy approved for live execution.

> **Mission:** Build a trustworthy MNQ historical backtester, find and validate
> one economically viable breakout/retest or liquidity-sweep/reversal strategy,
> paper trade it long enough to demonstrate reliable operation and acceptable
> risk, and **only then** consider an automated order-execution bot.
> Backtesting and paper trading are not interchangeable. TradingView Pine is
> a useful visual/secondary research reference; the Python engine remains
> the authoritative research implementation.

## Non-negotiable Git/branch isolation

- **Allowed target:** `feature/tradingview-pinescript` only for commits,
  document updates, code changes, experiments, and workflow updates
  undertaken under **this roadmap**.
- **Never write to `main` for this work.** No direct pushes, no force pushes,
  no merges/cherry-picks into `main`, no PR targeting `main`, no GitHub
  Actions workflow that writes to `main`, and **do not run** the current
  `deploy.sh` (it is designed for the `main` deployment checkout).
- Existing code and frozen artifacts on `main` may be **read-only
  references**. Do not modify or overwrite its scripts, configs, archives,
  live timers or historical research results. This branch-specific roadmap
  does **not** supersede `RULES.md` or authorize existing EXP runs.
- **Before EVERY write**, verify the remote target explicitly and stop if
  the branch is missing, detached, dirty with unknown edits or wrong:
  ```bash
  git branch --show-current
  git status --short
  git remote -v
  ```
  Do not make commits in a detached worktree. The pre-existing
  `/docker/trade-alerts-tv-audit` worktree was created detached for
  read-only auditing; its presence does not authorize commits.
- **Use explicit remote branch arguments on all GitHub API writes**:
  `branch="feature/tradingview-pinescript"`. If a future tool omits a
  branch argument or defaults to `main`, **do not call it**.
- When using an attached feature-branch worktree, push explicitly to
  `refs/heads/feature/tradingview-pinescript` only after reviewing the diff.
  Never use an ambiguous bare `git push` for this MVP.
- Protect against accidental merging by keeping this track **without a
  main-targeting PR**. Consider enabling GitHub ruleset/branch protection
  on `main` as an additional account-level safeguard. A Markdown document
  cannot technically prevent manual or external writes to `main`.
- Do not commit API keys, broker credentials, TradingView webhook secrets,
  browser login profiles, or raw vendor market-data binaries.

## Where we are — verified vs still pending

| Topic | Evidence / disposition |
| --- | --- |
| Python research engine | Existing structure/FVG/backtest/planner code; keep, do not rewrite |
| TradingView Pine baseline | Research-only V2 sweep/reversal, 2025-H1 **12 trades, 4 wins, 8 losses, -$16 after $0.50/side MNQ fees**; no proven edge |
| Direct Pine/Python check | **11/11** VPS targeted tests passed; **11,538** MNQ 1-minute chart bars compared: **0 FVG creation mismatches** and **66 raw MSS mismatching bars**; not a full entry-parity/data-quality certification |
| Barchart historical-data integrity | 2023–2025 individual-contract history **not yet accepted**. Inventory established seven incoming contracts with no earlier history in inspected files and six with unused Monday context. Determine which data are truly missing before downloading/rebuilding |
| Barchart downloader | `tools/barchart/download_history_repairs.py` and documentation exist on `main`; native site/download and exchange-history completeness still require evidence. Reuse/read as a reference, do not rewrite by default |
| Python R7 research | Corrected control can produce **zero accepted plans**, so adding filters cannot establish profitable improvement. `confirmation_first_family_v1` is a prepared research option; **EXP-030 run is still unproven/pending** |
| Live market data | The user reports ProjectX service discontinued; existing VPS ProjectX authentication is failing. **Do not repair ProjectX for this backtesting MVP** or treat those scheduled jobs as proof of paper-trading readiness |
| Order placement | **Not part of this MVP stage**. Do not connect or transmit brokerage orders |

Primary references, to consult read-only as needed:
- [Engineering and experiment safety rules](../RULES.md)
- [History inventory](contract_history_inventory.md)
- [Barchart repair acquisition protocol](barchart_history_repairs.md)
- [Python R7 research decision](research/r7_next_step.md)
- [Pine/Python September 29 direct comparison](../tradingview/backtests/mnq_20260929_morning_signal_audit.md)
- [TradingView reversal baseline](../tradingview/backtests/mnq_reversal_v2_2025H1_baseline_results.md)

## Stage 1 — Accept trustworthy historical MNQ input (**CURRENT**)

Goal: versioned, reproducible 2023–2025 **individual-contract** minute bars with
sufficient causal same-contract history and no undocumented gaps or roll mixing.

- [x] Audit inspected contract files against frozen raw segments and inventory evidence.
- [ ] Locate any original downloaded CSVs/normalized files **not included**
      in the inventory before requesting more Barchart downloads.
- [ ] Use the existing Barchart repair manifest/downloader to acquire only
      *proven absent* individual-contract windows. Verify each downloaded
      contract, 1m interval, Chicago time/date, first/last timestamp, OHLCV,
      hash, and overlap with existing trusted bars. Respect vendor login/quota.
- [ ] Classify holidays, Globex breaks, session omissions, DST, illiquid
      no-trade minutes, and rollover boundaries. Do not label every minute gap
      as missing data or assume a universal warmup duration.
- [ ] Check same-contract context needed by time-of-day RVOL (20 previous
      sessions), daily/HTF features and path-dependent liquidity/FVG/structure.
- [ ] If repair truly changes research inputs, build **new versioned artifacts**
      and provenance locks, preserving frozen controls; rebuild only affected
      subsets, not all years automatically.
- [ ] Record coverage acceptance per contract/year, unresolved exceptions,
      source SHA256s and dates in a small branch-only research note.

**Exit gate:** Accepted, traceable input coverage for every period included in
the next backtest; otherwise document exclusions and **do not** claim robust
strategy profitability.

## Stage 2 — Reproduce the corrected Python baseline

- [ ] Run only a targeted replay/test on accepted inputs; preserve existing
      chronology, contract isolation, session timing and completed-bar semantics.
- [ ] Reconcile baseline accepted-plan/trade counts and costs with frozen
      records. Do **not** substitute a legacy profitable baseline whose
      execution semantics differ.
- [ ] If an input repair changes outputs, document exactly which segment and
      trades changed. Investigate zero trades as a *decision/outcome*, not an
      automatic software error.
- [ ] Continue the already-prepared **EXP-030** only following an **explicit
      separate user `run 30` instruction** under `RULES.md` §17. The
      command `next`, `continue`, `commit`, or this roadmap does **not**
      authorize execution. Preserve prior EXP archives and source identity.
- [ ] Write one concise after-cost reproducibility report (inputs, code SHA,
      settings, test results, accepted plans, trade count, net P&L).

**Exit gate:** A repeatable corrected baseline whose data, event chronology,
fill assumptions and costs can be explained; no claim of positive expectancy
without evidence.

## Stage 3 — Select and test a *small* strategy candidate

- [ ] Restrict scope to **(A)** breakout and confirmed retest of relevant
      session levels, and **(B)** liquidity sweep/rejection → displacement →
      confirmed MSS → linked FVG → later hold (reversal), subject to Python
      strategy definitions and event-order constraints.
- [ ] Limit entries to the existing **09:30–10:30 America/New_York** window;
      use causal prior RTH/premarket/London levels where applicable.
- [ ] Compare the corrected control with **one preregistered change at a
      time**, chosen for a documented causal/structural reason. Don't relax
      filters just to manufacture trades or tweak stop/TP after seeing winners.
- [ ] Include contract point value ($2/MNQ point), realistic commissions,
      spreads/slippage, next-open entry, conservative ambiguous-bar handling,
      maximum holding, stop placement, TP policy, and no lookahead.
- [ ] Report per-trade ledger plus counts, net expectancy, profit factor,
      max drawdown, MAE/MFE, win/loss distribution, trade frequency and
      performance by setup and time.
- [ ] If results show too few valid trades or no after-cost edge, **stop
      rather than promote a strategy**. Separate implementation defects,
      overly selective hypotheses and unfavorable market outcomes.

**Exit gate:** One *fully specified* strategy version with repeatable,
economically plausible development results and explicit risks; otherwise
continue research, not bot execution.

## Stage 4 — Untouched out-of-sample validation

- [ ] Freeze candidate rules, costs and code SHA **before** evaluation.
- [ ] Preserve **2025 H2 as the untouched Pine V2 holdout** unless any
      previous usage requires selecting and locking an actually untouched
      alternative. Do not tune repeatedly on a holdout.
- [ ] Test the frozen model on distinct regimes/contracts as supported
      by verified history; assess drawdown, robustness and event counts.
- [ ] Reject/return to research if performance deteriorates or evidence is
      insufficient. Do not claim a profitable edge from 12 historical trades.

**Exit gate:** A documented pass/fail validation decision, with no cherry-
picked sample, no post-hoc model selection, and an explicit capital-risk plan.

## Stage 5 — Paper/shadow trade BEFORE any broker automation

- [ ] Only after Stage 4 passes, choose a **supported** read-only live
      market-data route. Barchart history and TradingView Pine are not
      automatically a low-latency live feed. Do not resurrect discontinued
      ProjectX auth or build an unused webhook stack in advance.
- [ ] Reuse the Python setup-state machine/planner and log **no trade**
      decisions as well as valid signals. Verify data freshness, correct
      active contract, no duplicate alerts, next-bar timing and restarts.
- [ ] Produce simulated entry/SL/TP, timestamp, reasoning and realistic
      simulated costs; **never transmit an order**.
- [ ] Capture at least **10** complete forward-observed sessions as an
      initial *operational* minimum; prefer **20+** and enough valid
      independent trades/regimes to evaluate risk and expectancy. Ten days
      alone cannot prove profitability.
- [ ] Compare decisions and fills with the broker/chart manually on sampled
      sessions; investigate timing differences and stability. Only advance
      if both economics and reliability justify it.

**Exit gate:** Explicit user review of forward results, error log, trade
frequency, net expectancy, drawdown and practical risk limits.

## Stage 6 — Evaluate an actual automated trading bot (**LATER; NOT AUTHORIZED**)

- [ ] First confirm broker/prop-firm rules and an authorized order API.
- [ ] Design a separate execution adapter with independent position sizing,
      daily loss cap, kill switch, stale-feed protection, maximum exposure,
      idempotent orders and reconciliation after restart/disconnection.
- [ ] Test in a true broker **simulation** environment with no real-money
      orders; confirm safeguards and fills under failures.
- [ ] Enable real-money automation **only following a separate explicit
      user decision** and satisfactory paper results. Neither this roadmap
      nor earlier requests authorize connecting an execution account now.

## Lean operating policy — one milestone at a time

1. Read only the **current gate** and its linked source material; don't
   reread/rebuild the entire research stack on every turn.
2. Before a code change, state the smallest intended diff and confirm the
   branch. Add **only focused regressions**. Existing core tests must not
   be weakened; use the relevant full suite when a change requires it.
3. Reuse existing scripts and artifacts instead of cloning whole systems,
   requesting the same CSV twice, or building overlapping dashboards.
4. Report what is **verified**, **inferred** and **not yet checked**.
   Never confuse source-matched TradingView OHLC with Barchart/contract
   data integrity; never label Pine proxy parity as Python strategy parity.
5. One branch-only commit/checkpoint per coherent completed task. Write
   next steps and blockers here; do not declare later stages done.
6. Stop for an explicit user decision before changing trading semantics,
   running a prepared EXP, opening any position or changing the data source.
7. If a task would require changing `main`, **STOP** and ask the user for
   a branch-only alternative. The instruction **never to write this MVP to
   `main`** takes precedence over convenience and old deployment instructions.

## Next action (precisely one)

**Resume Stage 1** by checking the **existing Barchart repair downloader**
and the 2026-10-10 history inventory, then determining whether the seven
missing earlier-contract windows have already been acquired elsewhere.
If not, run the downloader's smallest supported probe/one-window acquisition
and verify it. **No EXP-030 run, no full-year rebuild, no strategy tuning
and no ProjectX recovery are part of that action.**

When complete, update the Stage 1 checkbox and evidence here
**on `feature/tradingview-pinescript` only**.
