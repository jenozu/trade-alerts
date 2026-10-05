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
