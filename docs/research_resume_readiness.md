# Research resume readiness — 2026-10-05

## Decision

**Do not resume R7 strategy-selection experiments yet.** The engineering fixes
are implemented and tested on the review branch, but the strategy-fidelity
gate has a demonstrated historical decision mismatch and unresolved source-cache
verification. This is not evidence that the historical candles are generally
corrupt. Existing archived results remain preserved under their producer semantics.

This check did not change strategy code, weights, thresholds, caches, raw input
or archived results. It did not run a research experiment or deploy production.

## Repository and validation evidence

- GitHub main was verified at 3555c6f2266771a4480848689bd680e11c6365ae.
- Draft PR #7 was open and unmerged, with review head
  752ea34a27859d5304dc5b175295f50b038732e3 at inspection time.
- The inspected local checkout was 7b8e82935be724a06618c48b5b4cb4a8ca641803:
  tested review implementation plus a historical mismatch documentation commit.
- Fresh full regression: **650 passed, 443 warnings in 14.57 seconds** using
  the project virtual environment. Warnings report NumPy timedelta deprecation
  compatibility debt; they were not suppressed or treated as parity evidence.
- Verified 104 artifact hashes using 20 EXP archive manifests and the R4.5
  verification manifest, with no missing or mismatched files.
- Git comparison confirms research-archive contents are unchanged from starting main.
- The original instructions, current RULES.md, phases.md, refine-roadmap.md,
  checkpoint results, configs, fidelity/entry/data/lock documents and relevant
  backtest, planner, sequence, cache, lock and rollover code/tests were inspected.
- The January historical replay evidence is user-supplied VPS terminal output.
  No raw historical VPS files are available in this local checkout.

## What has passed, and what has not

| Area | Result | Meaning |
| --- | --- | --- |
| Commission/net accounting | PASS on review branch | Explicit units, point-value conversion, quantity and net-R regression coverage. The January replay still used zero commission. |
| Gap/slippage/next-minute execution | PASS for covered corrections | Adverse stop-open gaps, conservative terminal targets, stop-first ambiguity and stale-entry rejection are tested. Missing-path/session-liquidation policy is not certified. |
| Dataset classification | PASS | 2023–2025 are development data; 2026 is not automatically an untouched holdout. |
| New experiment identities | PASS for new locks | Inputs, code, configs and effective settings are locked and drift checked. Hashes do not prove feature causality or source correctness. |
| Confirmed entry timing | PASS for selected contract | The opt-in mode requires score eligibility plus fresh completed sequence/event and fills at the immediate next-minute open. |
| Full strategy fidelity | BLOCKED | Market entry, obstacles, structural stops, targets and invalidation do not yet share an executable contract with the planner. |
| Real source/cache roll isolation | NEEDS VPS VERIFICATION | Old source certification does not identify which generation path produced every current research cache. |
| Publication | REVIEW ONLY | Fixes are not on main; PR #7 remains a draft. Deployment is separate from research readiness. |

### Concrete fidelity blocker

At 2025-01-29 15:15 UTC, confirmed execution entered short at 21536.25 after
slippage; the production planner returned NO TRADE. Its risk-entry reference was
21560.25 and the first obstacle was the Asia low at 21553.25, seven points away.
The Asia low is already above the market fill. A planner zone price is not an
executed market price. Copying the seven-point rejection into market execution
would therefore be incorrect. Backtest fallback-stop and fixed-target rules also
differ from the planner's structural rejection and liquidity-objective rules.

Some green fidelity tests deliberately assert these mismatches. They establish
that a discrepancy is reproducible, not that it is resolved. Sharing setup-family
precedence does not make the two paths equivalent. See strategy_fidelity_audit.md.

The entry implementation consumes production sequence booleans. Those booleans
still allow same-row reversal progress and do not prove retest-object linkage,
separate continuation acceptance or post-retest micro-BOS. Such behavior must be
defined explicitly before certifying the selected strategy.

### Data verification boundary

The older Phase 12 audit records unadjusted contract data, 18 volume-cross-over
rolls, no duplicate timestamps and no null OHLCV. These are useful historical
source audit records, not evidence of universal corruption. The remaining check
is to match each exact 2023–2025 cache to its raw/config/producer identities and
prove segment isolation for FVG, displacement, structure and session-level
availability around actual rolls. The isolated replay intentionally reuses old
producer features and cannot establish current raw-to-feature parity.

### Research ordering boundary

refine-roadmap.md defines R7 as interaction experiments after R5 stop research
and R6 exit models. The tracked archives found here contain EXP-001 through
EXP-021 except the explicitly blocked EXP-012, and R4-05. No tracked R5/R6
completion evidence was found. Exit-research scripts alone do not prove that
those phases ran and were verified. Reconcile preserved completion evidence
before declaring R7 the next phase; do not rerun finished work unnecessarily.
The Research-Index.md also still describes EXP-002 as next, so it is not a current
completion authority.

## Ordered next tasks

1. Finish the versioned execution contract and implementation. Keep the selected
   confirmed next-open fill, existing score weights/thresholds and old baseline.
   Define causal obstacle checks relative to the price used for each decision,
   structural invalidation and rejection/cap policy, target/management rules,
   fill-window boundary and ambiguous sequence behavior. Separate planned zone
   references from actual fills. Use existing written requirements and the user's
   delegated choices; only genuinely unspecified trading semantics need input.
2. Add positive and rejected parity fixtures through the real shared paths for
   both directions/families, including the historical mismatch. Compare signal
   availability, eligibility, family, score, DOL, stop, targets and invalidation;
   distinguish intended next-open slippage from planned prices. Run focused and
   full regressions and commit each completed implementation task.
3. Run a bounded VPS replay in the isolated verification checkout. Verify original
   input locks before/after and collect a small durable decision-comparison report.
   Audit the exact 2023–2025 source/cache roll boundaries and producer paths.
   Never overwrite production, old caches or old ledgers. If an upstream definition
   must change, produce only the affected new versioned artifacts separately.
4. Establish a corrected, locked comparison baseline for the resolved execution
   contract. Keep the old historical control intact, quantify correctness changes
   separately, and include explicit commissions/slippage. Obtain the actual fee
   schedule before calling a run realistically cost-adjusted. Do not lower score
   thresholds merely because the confirmed sample is smaller.
5. Record the gate's evidence and resolve the R5/R6 completion record. Publish
   tested changes for review and merge the approved checkpoint into main. Once
   fidelity and cache checks pass, preregister the next development experiment
   and proceed to R7 if it is the verified next phase. Production deployment is
   not required merely to perform isolated development research.

A true forward holdout and final model freeze remain necessary before claiming
independent validation or accepting a production strategy. Their absence does
not by itself prohibit explicitly labelled development interaction research;
the present pause is justified by the unresolved fidelity/cache gate. Final
candidate freezing belongs after development choices, not before all R7 work.

## Subsequent implementation checkpoint

Later read-only VPS checks demonstrated cross-contract ATR contamination at all
five rolls in the exact frozen 2025 cache. Raw/cache timestamp values align;
their precision types differ. The January v2 rejection replay and its input lock
passed, but research cannot resume on these features. See
[rollover_cache_findings.md](rollover_cache_findings.md) for evidence, the preventive
single-contract pipeline guard and the separate-artifact rebuild requirements.

The delegated next task implemented an opt-in shared market-execution planner
and backtest path, documented in [market_execution_v2.md](market_execution_v2.md).
Both-direction/family synthetic price parity is now tested through real market
state. A v2 replay can report accepted/rejected decisions and retain old modes.
The research gate remains blocked pending actual historical replay, upstream
sequence/rollover checks and production-adapter verification where applicable.
This follow-up does not replace the inspection evidence or certify R5/R6 completion.

## Current gate after the historical build — 2026-10-05

The full 441,015-row source build passed all six contract segments and both
persisted locks independently verified. Do not repeat it or the five bounded
roll checks. Availability review found 846 score candidates: 20 lacked PDH/PDL,
19 failed family confirmation and real v2 rejected the remaining March 18 case.
See isolated_feature_build.md for exact counts and evidence boundaries.

Four new both-direction/family audit cases prove an older gap's retest can
confirm a newer setup whose new gap was never retested: event projection loses
gap identity before the sequence gate. This remains a material fidelity finding.
Same-row reversal and separate acceptance/micro-BOS also remain unresolved.
Full suite: 721 passed, 621 warnings; characterization tests do not clear the gate.

Next: resolve/test the versioned sequence contract, then prepare the locked
corrected baseline from preserved candidates, inspect historical v2 decisions
and realistic costs, and reconcile R5/R6 completion evidence. No more VPS commands
are needed for March 18. Do not deploy or resume R7 on feature-build success alone.
