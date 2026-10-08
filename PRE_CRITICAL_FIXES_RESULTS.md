# Pre-critical research integrity checkpoint

Starting main: `3555c6f2266771a4480848689bd680e11c6365ae`.
Scope: instructions.md and pre-critical-fixes.md (2026-10-02), supported by Manus audit at the same starting commit.
No weights, thresholds, setup selection, or research experiments are changed/run.

| Section | Status | Evidence |
|---|---|---|
| 1 Commission / net accounting | PASS | Per-contract point accounting, explicit points/dollars conversion and quantity totals; 29 targeted tests; full suite 582 passed, 300 warnings. |
| 2 Execution invariants | PARTIAL | 39 targeted tests; full suite 592 passed, 340 warnings. Definite gap-fill bugs fixed; missing path/session liquidation remains uncertified. |
| 3 Dataset freeze | PARTIAL | Classification PASS (3 new tests); forward model freeze not established while fidelity is unresolved; 595 passed, 340 warnings. |
| 4 Input fingerprinting | PASS for new locks | Deterministic/tamper/drift/immutable archive tests; 604 passed, 340 warnings. Old producer provenance remains explicitly partial where unavailable. |
| 5 Strategy fidelity | PARTIAL / BLOCKED | Audit and six new fixtures complete; material entry/target/sequence mismatches require strategy decisions, real-cache parity requires VPS. |

## Section 1

Files: src/backtest.py, config/strategy.yaml, tests/test_backtest.py,
docs/backtest_accounting.md. Net points now deduct commission, net R uses net
points. Regression tests cover both directions, disabled/zero/nonzero commissions,
NQ/MNQ dollar conversion, multiple contracts and invalid units/quantity.
One-contract disabled-cost schema remains unchanged. Partial exits are separate
research code, not implemented in baseline; their transaction accounting is not
certified here. Existing archives were neither changed nor regenerated.

## Research gate

**Strategy-changing research is NOT safe to resume yet.** Accounting and input-lock
engineering is tested, but strategy parity is not established. Diagnostic/archive
reproduction may continue; no new selection experiment was started.

## Section 2

Files: src/backtest.py, tests/test_backtest.py, docs/backtest_execution.md.
Five new regression cases failed before correction; now both stop-gap directions,
known-open terminal-target priority and stale next-session entry rejection pass.
Other cases cover both-direction ambiguity, timeout/gaps and end-of-data costs.
Commission commit: `2092ff8`. Gap fixes intentionally change replay on affected
paths; no frozen archive has been overwritten. Real-cache impact requires VPS
verification. Session liquidation and missing-path fills need explicit policy/data.

## Section 3

Files: config/research_policy.yaml, src/research_policy.py,
tests/test_research_policy.py, docs/research_dataset_policy.md and
docs/integrity_checkpoint.json. Permanent dataset labels reject unsupported
holdout claims. Configuration identity is checkpointed without falsely declaring
an approved forward model freeze. Section 2 commit: `de94173`.

## Section 4

Files: src/experiment_identity.py, scripts/lock_experiment_inputs.py,
scripts/archive_experiment.py, scripts/certify_feature_cache.py,
scripts/run_cached_backtest.py, tests/test_experiment_identity.py,
docs/experiment_input_locks.md. Existing feature-cache SHA-256 helper is reused.
Archive CLI requires verified input identity; locked archives and certification
metadata cannot be silently overwritten. Cached backtests lock inputs before
simulation and verify afterward. 9 new tests; 14 related tests pass.
Section 3 commit: `bc5283a`. No historical producer facts were invented.

### Section 4 integration follow-up

A real cached-backtest CLI smoke test exposed an existing all-null optional SNR
report failure. A failing regression test was added, and numeric coercion now
preserves missing values rather than comparing None. Full suite: 605 passed,
342 warnings. Fingerprinting commit: `041ca73`.

## Section 5 — completed audit, unresolved fidelity gate

Files: docs/strategy_fidelity_audit.md, tests/test_strategy_fidelity.py. Six new
fixtures cover positive-plan vs baseline mismatches, score/sequence independence,
same-row reversal/FVG ordering assumptions, window metadata, real-stage synthetic
raw replay through alert, and rollover-gap FVG isolation. Related suite: 64 passed,
29 warnings. Full suite: **611 passed, 350 warnings in 12.49s**.

Synthetic raw replay proves feature/state/planner/alert append invariance. It does
not establish positive-entry parity on actual source data. In the positive fixture,
score/direction/entry/stop agree, but a HYPOTHESIS becomes a baseline trade and the
market-derived targets differ from baseline fixed distances. Family/confirmation/
invalidation are absent from the baseline ledger. No scoring weights were changed.

Production continuation waits for a later FVG retest, but does not independently
prove acceptance duration, retest-object linkage or a later micro-BOS. Reversal
sequence permits several events in one OHLC row. The baseline does not require
production sequences. RULES.md section 6 prohibits inventing these semantics.

## Commits and verification

| Commit | Work | Full suite |
|---|---|---|
| 2092ff8 | Commission units, net/R, quantity accounting | 582 passed, 300 warnings |
| de94173 | Gap fills and execution invariants | 592 passed, 340 warnings |
| bc5283a | Development classification / holdout policy | 595 passed, 340 warnings |
| 041ca73 | Immutable experiment input locks / cache provenance | 604 passed, 340 warnings |
| 80fe7c0 | Integration-discovered missing SNR report defect | 605 passed, 342 warnings |
| See Git history for fidelity audit commit | Audit and six fidelity fixtures | 611 passed, 350 warnings |

The cached-backtest CLI was run on a certified synthetic four-bar cache from a
clean commit; one trade and all reports were produced, and its input-lock CLI
verification passed. This is an integration check, not an experiment selecting a
strategy. No raw feature pipeline was rebuilt for ledger-only verification.

EXP-001 was reproduced from the tracked EXP-005 classified ledger split by source
year: all serialized metrics exactly match the frozen EXP-001 JSON (1,218 trades).
Every research-archive file remains identical to starting main according to Git.
Costs-disabled accounting is preserved. Gap-fill/stale-entry corrections intentionally
change new simulations on affected paths: old archives retain old execution
semantics, and any corrected replay requires versioning and original VPS inputs.
No archive, expected output, or source dataset was regenerated/replaced.

Runtime: Python 3.12.14, pandas 2.3.3, NumPy 2.5.3, pyarrow 23.0.1, pytest 9.1.1;
installed declared requirements into the project virtual environment. Warnings are
existing timedelta/datetime compatibility debt plus increased exercised cases;
they are reported, not suppressed. Dependency ranges were not changed. Older
PHASES_TRUTH_AUDIT.md remains historical; this checkpoint is the current test evidence.

## Exact remaining blockers

1. **Remaining strategy semantics:** the entry-method choice is resolved below;
   remaining issues include acceptance and post-retest BOS,
   object/level linkage, whether same-row reversal events count, hard stop cap,
   market-derived vs fixed research targets, and signal-time vs fill-time window.
   Existing source materials establish a retest intent but not all deterministic
   order/fill rules. Changing these without that contract would silently change
   the tested strategy. The audit lists the current implementations and gaps.
2. **VPS inputs/access:** preserved raw/certified caches and original producer
   configs/manifests for 2023–2025 are absent here. Verify exact contract/roll
   provenance, adjustment status, volume crossovers, segment isolation and
   prior-day/premarket levels around rolls. Replay real paths to quantify impact
   of corrected stop-gap/stale-entry behavior and compare positive live/backtest
   entries/stops/targets/invalidation. Do not infer these facts from ledger hashes.
3. **Forward freeze:** after fidelity decisions/parity evidence, declare a versioned
   model freeze and preregister an actually untouched future validation period.
   Current checkpoint hashes are not an approved forward model or holdout start.

## Conclusion

All five sections have been worked through sequentially; locally provable fixes,
tests, classifications, fingerprinting and audit are implemented. Full regression
passes and frozen artifacts are preserved. **The pre-critical research gate remains
PARTIAL/BLOCKED, so strategy-changing research must stay paused.** The remaining
work depends on explicit strategy semantics and unavailable VPS evidence, not on
an unperformed local engineering task. No EXP-002/new selection research began.

## Publication verification

Published as draft PR [#7](https://github.com/jenozu/trade-alerts/pull/7) on
`research/pre-critical-integrity`; main remains at starting commit 3555c6f.
Automatic approval review rejected the direct default-branch push because of
shared-branch impact. A review branch is the safer publication route. Shell Git
lacked write credentials; the connected GitHub tools published the tested trees.
Connector-created commit metadata produces different commit IDs; every remote
tree was verified equal to the corresponding tested local Git tree.

| Tested local commit | Published review-branch commit |
|---|---|
| 2092ff8 | a7d5c03 |
| de94173 | 5006bd1 |
| bc5283a | a8f92db |
| 041ca73 | d275ef8 |
| 80fe7c0 | 4fc85a6 |
| 588b116 | 8d7a58d |

The earlier checkpoint code hash and test history refer to local commits above;
this mapping preserves their remote content identity. Final documentation-only
publication records do not change tested code or experiment artifacts.


## Selected entry-method follow-up — 2026-10-03

User delegated the limit-vs-market decision. **Selected: next one-minute bar open
following completed retest confirmation**, version market_after_retest_confirmation_v1.
Implementation requires existing score eligibility plus a fresh production-family
sequence/event, explicit completion/window metadata, timely confirmation availability
and the immediate next minute. Adverse slippage applies. Shared family precedence
matches the live planner; a high-scoring unconfirmed opposite side cannot block a
confirmed candidate. Ledgers record execution version, family and confirmation time.

The archived score_signal_v1 baseline remains explicit and is not silently replaced.
A cache-runner execution override is included in effective input-lock settings.
No weights, thresholds, historical selections or archived outputs were changed.
Tests cover both directions/families, missing/false/string confirmation fields,
late availability, completion/window gating, fresh-event eligibility, conflicting
family context, adverse fills, append invariance and legacy parity. All 20 new
regression cases pass; related suite **76 passed, 128 warnings**; full suite
**631 passed, 403 warnings in 12.24s**. Warnings remain reported compatibility debt.

Files: src/backtest.py, src/setup_family_contract.py, src/trade_planner.py,
scripts/run_cached_backtest.py, config/strategy.yaml,
tests/test_confirmed_entry_execution.py, docs/confirmed_entry_execution.md,
docs/strategy_fidelity_audit.md, phases.md and this checkpoint document.

Entry-method approval is no longer a blocker. The gate remains PARTIAL/BLOCKED
because full stop/target parity, fine sequence semantics and original VPS evidence
are still unresolved. This follow-up does not declare a forward model freeze.

Confirmed-mode integration verification: a certified synthetic five-bar cache
produced one fresh reversal entry through the actual cache-runner CLI. The
execution override was present in the input lock, standalone lock verification
passed, and ledger execution/family/confirmation metadata matched the selected
contract. This is an integrity smoke test, not strategy-selection research.

Entry-mode code commit: tested local `30e8cbe`, published `b7722ae` on draft PR #7;
Git trees were verified identical (`27445f10bbd6ac9bcfa7274f60fc5ed3d17823d3`).


## Isolated historical replay tooling — 2026-10-04

VPS verification checkout passed the prior 631-test suite. User-supplied VPS
checks show original 2025 warmup raw/scored/config hashes match cache metadata.
Three current feature files differ from the cache producer: fvg.py, pd_arrays.py,
scorer.py. All eight confirmation columns exist as booleans; raw/scored inputs
lack explicit completion fields. The input audit reports 352,125 evaluation rows
for 2025 and source-file/contract segment provenance. These are user-provided
terminal findings, not a completed real-data replay or rollover certification.

Added scripts/run_isolated_cache_replay.py with a separate diagnostic provenance
contract, documented in docs/isolated_cache_replay.md. It verifies frozen producer
blobs at the recorded Git commit rather than claiming current feature-code
compatibility; no current features are generated, no validation bypass flag is
used, and original metadata is not recertified. Timing is derived under an
explicit historical-export assumption, preserving restrictive existing metadata.
A date-bounded derived Parquet, locked inputs and separate legacy/confirmed
ledgers are written only to a fresh directory outside the production source tree.
Original inputs are checked after simulation. Vendor live correction/latency
history and CSV-specific timing remain uncertified.

Validation: 19 new tests, including actual two-mode backtests and locked-file
verification, unchanged source hashes, producer mismatch rejection, unsafe output
rejection, completion boundaries, malformed times and date-bounded reads.
Full regression: **650 passed, 443 warnings in 12.51s**. Real VPS replay has not
yet run. The research/deployment gate remains **PARTIAL/BLOCKED**; no selection
experiment ran and no frozen research archive was regenerated.

## Research-resume recheck — 2026-10-05

See [docs/research_resume_readiness.md](docs/research_resume_readiness.md) for the
current gate and ordered remaining tasks. Fresh full regression: **650 passed,
443 warnings in 14.57s**. Verified 104 archived artifact hashes with no failures;
all research-archive content remains unchanged from starting main. GitHub main
is still 3555c6f; draft PR #7 is open and unmerged.

The isolated first-week and January VPS diagnostic replays have now run with
unchanged inputs. The January confirmed entry is a demonstrated planner/backtest
decision mismatch, detailed in docs/strategy_fidelity_audit.md. These diagnostics
advance verification but do not clear stop/target/sequence or rollover-cache
fidelity. **R7 strategy-selection research is not approved to resume yet.**

No tracked R5/R6 completion evidence was found during the recheck; reconcile the
preserved experiment record before declaring R7 next. An untouched forward
holdout remains required for independent validation and production acceptance;
it is not by itself a prerequisite for development-only R7 experiments once the
current fidelity/input gate is cleared.

## Shared market-execution implementation — 2026-10-05

Implemented market_after_retest_confirmation_v2 as an explicit opt-in version.
It shares the planner's structural/obstacle/liquidity decision construction at
the actual next-open entry reference, rejects structural risk over 25 points
without fixed fallback, and preserves the TP4 full-position policy. Missing
runner objectives are explicit rejections. Legacy versions remain unchanged.

The API task was committed after 666 passing tests; the integration adds real
market-state/backtest parity and isolated rejection reporting. Full regression:
**685 passed, 583 warnings**. See docs/market_execution_v2.md. The gate remains
PARTIAL/BLOCKED pending real VPS replay and upstream/adapter fidelity checks.
No scoring weights, raw data, preserved caches or archives were changed.

Both actual cache-runner CLIs and standalone input-lock verification passed on
a fresh synthetic v2 fixture from clean committed code. Original source hashes
were unchanged. Full regression after final code changes: **685 passed, 583
warnings in 13.31s**. The next bounded VPS command is in docs/market_execution_v2.md.

## Historical rebuild and sequence audit — 2026-10-05

All five bounded historical contract-isolation diagnostics passed, followed by
the full 441,015-row, six-contract feature-only build. Inputs stayed unchanged;
both input/output locks independently verified on the VPS. Review retained
352,125 UTC-year-2025 bars and found 846 score candidates. Of 20 candidates
missing prior-RTH levels, 19 failed family confirmation; real v2 rejected the
remaining March 18 short for 92-point structural risk and unavailable TP1.
This is a diagnostic rejection, not performance or positive historical parity.
See docs/isolated_feature_build.md for paths, counts and limitations.

Four new characterization cases expose an old gap's retest confirming a new
setup through real FVG projection, family sequence and shared entry-gate calls.
Both directions/families reproduce the loss of gap identity. Focused tests:
25 passed, 15 warnings; latest full suite: **721 passed, 621 compatibility
warnings in 17.45s**. No production entry rules, raw files, old caches, scoring
parameters or research archives changed. New feature outputs remain candidates.

The research gate is still PARTIAL/BLOCKED by sequence fidelity and corrected
baseline/historical parity checks. Do not repeat passed roll/build checks. The
next task is the versioned object/chronology contract, then the locked baseline
with actual fees and R5/R6 evidence reconciliation; R7 remains paused.

## Object-linkage correction — 2026-10-05

Implemented opt-in `fvg_object_linked_v1` derivation and shared v2 execution
activation. Only a directional post-trigger gap's own later retest can confirm
the setup. Original columns/defaults remain preserved; missing or inconsistent
linked evidence fails closed. The public market planner and actual backtest
agree on accepted/rejected both-direction/family fixtures. No scoring change,
production migration, historical overwrite or selection experiment occurred.
See docs/linked_sequence_contract.md for scope and remaining chronology limits.
Full regression: **738 passed, 704 reported compatibility warnings in 17.33s**.

## Linked derivation runner — 2026-10-05

Added a feature-only runner to reuse the completed isolated build and retained
FVG lifecycle evidence. It checks original producer blobs, input/output locks,
creation geometry and projected events; every original feature column is retained
exactly. Linked features and both new locks go to a fresh sibling directory.
No full feature pipeline, backtest, production alert or research selection runs.
Historical VPS execution remains required; its exact command is in
docs/linked_sequence_contract.md. The original lifecycle CSVs lacked an earlier
output lock and are now explicitly locked/consistency checked, not retroactively
described as having immutable provenance. Six new integration/provenance tests.
Latest full regression: **744 passed, 711 compatibility warnings in 20.14s**.
Committed CLI `bc47f9e` completed on the real-stage two-contract synthetic build;
both independent lock verifications passed. Historical derivation is the next
VPS task, with no upstream feature-pipeline rerun. Tested linkage code: `e5fb742`.

Historical linked derivation now passed on all six contracts, retaining 441,015
rows with unchanged inputs. Both saved locks independently verified on VPS.
Focused VPS suite: 23 passed, 95 warnings. See linked_sequence_contract.md for
the exact output path and per-family counts. Those are full-history confirmation
events, not score-eligible trades or historical execution parity. No rerun is
needed; next inspect actual 2025 eligibility and bounded execution decisions.

The actual 2025 overlap check now passed: 846 score-candidate rows produce 15
linked eligible directional signals (9 reversal, 6 continuation), with output
lock verified before/after. Per-contract/direction counts are retained in
linked_sequence_contract.md. These are not accepted execution plans or trades;
next evaluate the 15 signals through v2's shared risk/target decision API.

The historical v2 decision task is now complete: **15 checked, 0 accepted plans**,
with output lock verified before/after and no simulated trades or changed files.
Thirteen exceeded the structural-risk cap; the remaining two failed obstacle
room or fill-window checks. Other rejection reasons may coexist. Exact evidence
and limits are in linked_sequence_contract.md. Do not repeat this check or tune
thresholds to manufacture accepted trades. Remaining chronology/continuation
fidelity, accepted historical-path evidence, actual fees and R5/R6 reconciliation
still prevent clearing the research gate.

## Local chronology and durable diagnostic checkpoint

Implemented opt-in `fvg_chronology_v2`: earlier completed sweep before
displacement/MSS; continuation hold of the frozen broken swing before its own
FVG retest, then a later close through the internal swing frozen at that retest.
These conservative semantics use the user's delegated choices and are explicit
in docs/chronology_sequence_contract.md. Existing feature columns, contracts,
scoring and production defaults remain preserved. Real planner/backtest accepted
and rejected fixtures prove both-direction/family parity and future invariance.

The versioned derivation runner and new locked execution diagnostic are locally
tested. They reuse the completed isolated build, preserve original producer
identities and save decisions/diagnostic trades under fresh output locks.
Realistic fee certification and historical chronology evidence still need VPS/
user inputs; no research-selection experiment or deployment occurred.

Read-only remote-ref reconciliation found completed R5 and R6 study records,
plus preserved R7.0 outputs, outside main/the review checkout. R5/R7 manifests
verified 135 Git-blob artifacts. The R6 fixed-target/partial-exit block is reviewed;
not every original EXIT-A–E definition is independently certified. R7 roadmap
completion boxes are stale relative to archived outputs. See
docs/research_branch_reconciliation.md; do not blindly rerun completed research.

Latest full regression: **779 passed, 862 reported compatibility warnings in
23.24 seconds**. No existing archive changes relative to starting main.
The engineering tasks are locally proven; overall item 5 remains PARTIAL / NEEDS
VPS VERIFICATION. This checkpoint does not authorize resuming R7 yet.

Historical chronology job now completed on all six segments, with unchanged
inputs and the audit's two locks verified according to supplied VPS terminal
evidence. Result: **7 eligible signals, 0 accepted plans, 0 simulated trades**.
The saved four-lock independent check and rejection review are next; no job
rerun or score tuning is required. Details/path are in
docs/chronology_sequence_contract.md. Historical accepted-path/cost proof is not
established by this zero-trade diagnostic, so R7 remains paused.

Independent verification of all four feature/execution locks now passed on the
unchanged producing VPS checkout. Rejection review accounts for all seven
reversal signals: six exceed structural risk 25; one fills at the excluded
10:30 ET boundary. Secondary obstacle/asymmetry reasons are documented. The
2025 diagnostic is complete; next inspect preserved 2023/2024 metadata/artifacts
read-only, without a rebuild or repeat of any completed 2025 check.

## 2024 corrected diagnostic and 2023 source handling — 2026-10-08

Supplied VPS terminal evidence confirms the separate 2024 contract-isolated
build at `/root/trade-alerts-verify-YwIqEc/replays/isolated-2024-v_r21v9e/features`:
441,600 source bars, 353,745 UTC-2024 bars, six segments. Both feature locks
independently verified, every segment's ATR/level/sequence reset and availability
checks passed, and all four original source roles plus original cache metadata
remained unchanged. Preserved 2023 and 2024 feature controls both showed ATR
crossing all five contract boundaries; regeneration is required for these new
corrected diagnostics. Original archives and raw candles are preserved.

The sibling `chronology` derivation and `execution` audit completed with unchanged
inputs and verified locks. Two UTC-2024 reversal signals were eligible; neither
was accepted. January 26 14:30 UTC long needed a 32-point structural stop,
had only 0.25 points to the first obstacle and failed minimum asymmetry. June 24
14:17 UTC short needed 27.5 points. Both exceed the frozen 25-point cap. Zero
trades supplies rejection evidence, not historical accepted-path proof. R7 is
still paused; no thresholds or risk rules were relaxed.

2023 raw and preserved scored-control timestamps/contracts/OHLCV were compared:
440,032 ordered unique bars, 2022-10-02 22:00 UTC through 2023-12-29 21:59 UTC,
zero mismatches. Raw SHA-256:
`d4be2d6668de6e341bbb860a50a89ba156dc5f92486199f68991642d3fb0248d`.
No original 2023 cache producer metadata was found. The feature-build CLI now
supports an explicit preserved-source manifest as an alternative to cache
metadata. It requires hashed raw/control/strategy/session files under the source
root and explicitly declares original producer provenance unavailable; it rejects
invented producer identities. New build code, data and configs are fully locked.
This does not retrospectively certify the old scored control. Existing cache
producer verification remains unchanged. No 2023 build has run yet.

Validation for this adapter: focused suite **16 passed, 31 warnings**; full
regression **786 passed, 872 warnings in 47.90 seconds**. Warnings remain reported
compatibility/performance warnings. The review branch remains separate from
main. A read of current main found `cfa451884d3374ef40ed8d6daf56ef9e6a96a082`
adding an EXP-001 VPS wrapper; this work neither edits nor runs that wrapper.
