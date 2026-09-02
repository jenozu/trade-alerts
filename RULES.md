# `trade-alerts` Engineering Rules

These rules apply to any human or AI agent modifying this repository.

## 1. Correctness Before Green Tests

A passing test suite is required, but making tests green is not the ultimate goal. The goal is a correct, deterministic trading research system whose backtests do not use information that would not have been available at the simulated time.

Never change valid behavior merely to satisfy a test.

## 2. No Look-Ahead Bias

Future information must never affect historical outputs.

This applies to, among other things:

- session levels;
- resampled bars;
- swing confirmation;
- structure labels;
- liquidity events;
- FVGs;
- volume statistics;
- support/resistance calculations;
- bias features;
- entries/exits;
- completed trades.

Appending future bars must not rewrite an already-finalized historical result unless the specification explicitly defines that result as developing/revisable.

## 3. Time Semantics Are Part of the Strategy

Timezone handling, session boundaries, candle-close timing, `as_of` behavior, rollover dates, and incomplete bars are strategy-critical behavior.

Do not silently alter them.

Naive timestamps should be rejected or normalized only according to an explicit project rule.

## 4. Developing vs Finalized Data

Features that are allowed to develop intrabar or intraday must be clearly distinguished from finalized features.

Do not expose finalized values before they would have been knowable in real time.

## 5. Tests Are Contracts

Do not delete, skip, xfail, weaken, or broadly relax legitimate tests just to obtain a passing suite.

Changing an expected value requires evidence from the written specification or an explicit strategy decision.

Every bug fix should preserve existing regression coverage and add a regression test when appropriate.

## 6. Strategy Ambiguity Requires Escalation

An engineering agent may fix implementation errors autonomously, but it must not invent trading semantics.

Examples that require escalation when not already specified:

- wick break vs candle-close confirmation;
- exact MSS/CHoCH/BOS definition;
- sweep/reclaim requirements;
- which swing qualifies as protected/weak;
- session high/low inclusion boundaries;
- whether an incomplete bar can confirm a feature;
- TP/SL priority when both are touched within data resolution;
- entry timing when a signal occurs mid-bar.

If two plausible implementations would produce different trades, returns, or historical signals, treat the issue as strategy-significant.

## 7. Small, Reviewable Changes

Prefer the smallest root-cause fix.

Do not mix unrelated cleanup, formatting, refactors, or dependency changes into a focused bug fix.

Preserve public APIs unless an intentional interface change is part of the task.

## 8. Determinism

Tests and backtests must be reproducible.

Avoid dependence on:

- wall-clock time unless explicitly controlled;
- unordered iteration when order matters;
- network services in unit tests;
- random values without fixed seeds;
- machine-specific file paths in core logic.

## 9. Validation Sequence

For a code change, use this progression where applicable:

1. failing test only;
2. relevant test file;
3. related subsystem tests;
4. full test suite.

A task is not complete until the full appropriate suite passes.

## 10. Git Safety

Before modifying code, inspect the working tree.

Never automatically destroy unknown user work.

Forbidden without explicit instruction:

- `git reset --hard` against user changes;
- force-push;
- deleting untracked user files merely to clean status;
- rewriting shared history.

Do not commit secrets or credentials.

## 11. Environment Safety

Use the project virtual environment.

Do not globally install or upgrade packages on the VPS when a project-local change is sufficient.

Dependency changes must be intentional, documented, and tested.

## 12. Efficient Agent Operation

AI agents should minimize unnecessary token/API usage:

- use concise test output during debugging;
- inspect only relevant files and line ranges;
- use targeted search before broad reads;
- avoid repeated full-repository summaries;
- avoid verbose narration during autonomous loops;
- reserve expensive reasoning models for difficult problems.

Cost efficiency must never justify skipping required tests or making speculative fixes.

## 13. Warnings

Warnings do not fail the build unless configured to do so, but they must be reported.

Warnings that indicate future breakage, numerical changes, timezone problems, or deprecated behavior affecting correctness should be tracked and addressed deliberately.

## 14. Completion Standard

A coding/testing task is complete only when:

- the requested behavior is implemented or verified;
- focused tests pass;
- the full relevant suite passes;
- no unexpected working-tree changes remain unexplained;
- the diff has been inspected;
- any commit/push requested by the workflow succeeds;
- strategy-significant assumptions are documented rather than silently invented.

## 15. Priority Order

When rules conflict, use this priority:

1. protect credentials and user data;
2. preserve backtest integrity / prevent future leakage;
3. follow explicit trading-strategy specifications;
4. preserve validated behavior and test contracts;
5. make the smallest correct engineering change;
6. optimize runtime and AI/API cost.
