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
| 5 Strategy fidelity | PENDING | |

## Section 1

Files: src/backtest.py, config/strategy.yaml, tests/test_backtest.py,
docs/backtest_accounting.md. Net points now deduct commission, net R uses net
points. Regression tests cover both directions, disabled/zero/nonzero commissions,
NQ/MNQ dollar conversion, multiple contracts and invalid units/quantity.
One-contract disabled-cost schema remains unchanged. Partial exits are separate
research code, not implemented in baseline; their transaction accounting is not
certified here. Existing archives were neither changed nor regenerated.

## Research gate

Research remains paused until the remaining sections are assessed.

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
