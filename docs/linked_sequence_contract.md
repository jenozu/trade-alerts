# FVG object-linked confirmation v1

The supplied NotebookLM framework calls for a pullback to the resulting FVG
after a valid displacement/structure shift. An unrelated older gap's retest
does not establish that sequence. The four legacy characterization tests remain
as evidence of the boolean-path discrepancy.

`src/linked_sequences.py` implements the explicit opt-in contract
`fvg_object_linked_v1`. It consumes complete same-contract scored bars and the
tracked FVG object table, preserving every original column and adding linked
family flags and the confirming object's identity. It does not alter the score.

For reversal, the existing core-completion event starts the setup. For
continuation, the existing displacement structure-break event starts it.
Only directional gaps created on or after that trigger qualify. Confirmation
requires a strictly later retest of that same object, before invalidation and
within the existing ten-bar setup lifetime. A new trigger resets the association.
If several eligible objects retest together, the latest creation wins; stable
identity breaks equal-time ties. There is one fresh confirmation event, with
active context retained until reset/expiry. Source bars must be unique, ordered,
timezone-aware and from one known contract when labels are present. Missing,
duplicate or inconsistent object evidence fails closed.

Execution opts in with `backtest.sequence_contract: fvg_object_linked_v1` and
`backtest.execution_model: market_after_retest_confirmation_v2`. The backtester
requires the linked feature schema; the public market-execution planner checks
the same flags and object identity from real market state. Both retain the
selected contract and planner decisions retain `confirmation_fvg_id`. The
existing structural stop, obstacle, target, fill-window and cost policies remain.
There is no permissive fallback to aggregate confirmation.

The default remains `production_boolean_v1`; legacy results and production
hypotheses are preserved. Selecting the linked contract with a score-only or
confirmed-v1 executor is rejected. No production default was migrated.

This is deliberately the object-linkage correction. It does not resolve whether
same-row sweep/displacement/MSS can establish the core, impose a separate
acceptance duration or implement a newly defined post-retest micro-BOS. IFVG-only
and structural-level-only retests are not added. These are independent fidelity
boundaries; this task does not clear R7 or certify a research cache.

Tests use real linked derivation, market state, planner and backtest calls for
positive and unrelated-object rejections in both directions/families. Other cases
cover same-creation-bar retests, expiry, invalidation, append invariance, malformed
identity/timing, missing execution evidence and exact old-mode ledger parity.
Related suite: 60 passed, 229 warnings. See the checkpoint for full regression.

Next historical step: derive a new locked artifact from the completed isolated
features and their saved FVG lifecycle evidence. Preserve that build and its
locks, verify original inputs before/after, and retain the new feature/decision
identity separately. This is not a repeat of the full upstream feature pipeline.

## Isolated historical derivation

`scripts/derive_linked_sequences.py` checks both preserved build locks. Original
code is checked against recorded Git blobs, so updating the review checkout does
not falsely classify an expected code change as altered historical data. Every
non-code input must still match on disk. Each source feature file must match its
locked hash, contract and row count. Retained FVG lifecycle geometry and projected
touch/retest/fill events must match those features. The saved lifecycle CSVs were
not in the old output lock: their current identities are now locked and their
consistency checked, without claiming previously recorded immutable provenance.

Only new linked columns are added. Every original feature column is checked for
exact equality. New source/output locks and LINKED_SEQUENCE_SUMMARY.json are
written to a fresh sibling directory; no backtest, recertification or alert runs.
Six new tests include real stage generation followed by actual derivation, both
independent locks, source preservation, output drift and mismatched lifecycle/
path rejection. Only Git cleanliness is patched during dirty test development;
feature stages, lifecycle projection, locks and Git-blob checks are real.

Run this once in the existing verification checkout, using its sibling venv:

```bash
cd "$HOME/trade-alerts-verify-YwIqEc/repo" &&
git fetch origin research/pre-critical-integrity &&
git merge --ff-only FETCH_HEAD &&
../venv/bin/python -m pytest -q tests/test_linked_sequences.py tests/test_linked_derivation.py &&
trade_linked_output="$PWD/../replays/linked-2025-$(date -u +%Y%m%dT%H%M%SZ)" && {
nohup ../venv/bin/python -u scripts/derive_linked_sequences.py \
  --source-build "$HOME/trade-alerts-verify-YwIqEc/replays/full-2025-isolated-features-20261005T185645Z" \
  --output-dir "$trade_linked_output" \
  > "$trade_linked_output.log" 2>&1 < /dev/null &
printf 'Started PID %s. Log: %s\n' "$!" "$trade_linked_output.log"
}
```

Completion marker: `LINKED DERIVATION: completed; original inputs unchanged;
research readiness pending`. A traceback is a failed check; do not overwrite or
restart the original build. The derivation processes the full retained source
history but does not repeat resampling, bias, indicators or scoring. Its elapsed
runtime on the VPS has not been measured. Retain the printed output path for the
next read-only evidence check. R7 stays paused pending the remaining fidelity gate.

Committed implementation `bc47f9e` passed the actual CLI on a real-stage two-
contract synthetic build, preserving its original inputs. Both new locks passed
standalone verification afterward. Full regression: 744 passed, 711 reported
compatibility warnings in 20.14s. Historical derivation remains pending on VPS.

## Historical derivation passed — 2026-10-05

User-run VPS evidence reports 23 focused tests passed with 95 warnings in 4.25s,
followed by successful six-segment derivation. Output:
`/root/trade-alerts-verify-YwIqEc/replays/linked-2025-20261005T205750Z`.
Original inputs remained unchanged. Both EXPERIMENT_INPUT_LOCK.json and
LINKED_OUTPUT_LOCK.json independently returned VERIFIED against the unchanged
verification checkout. All 441,015 rows are retained.

| Contract | Rows | Bullish reversal | Bullish continuation | Bearish reversal | Bearish continuation |
| --- | ---: | ---: | ---: | ---: | ---: |
| NMZ24 | 75,315 | 204 | 964 | 198 | 1,052 |
| NMH25 | 85,772 | 253 | 1,218 | 276 | 1,360 |
| NMM25 | 86,668 | 282 | 1,159 | 272 | 1,209 |
| NMU25 | 89,715 | 227 | 1,129 | 247 | 1,195 |
| NMZ25 | 88,590 | 249 | 1,171 | 274 | 1,262 |
| NMH26 | 14,955 | 45 | 192 | 52 | 219 |

These are fresh linked confirmation event counts over all retained history,
including pre-2025/context bars. They are not 2025 score-eligible trade counts or
accepted execution plans. Status remains LINKED_FEATURE_CANDIDATE_NOT_RESEARCH_READY.
Do not repeat this derivation or the full feature build. Next inspect overlap
with 2025 directional score candidates through the actual shared family gate,
then bounded v2 execution evidence. Remaining chronology findings still apply.
Historical counts and lock findings are transcribed from user terminal screenshots;
the source artifacts remain on the VPS and are not locally reproduced.

### 2025 score / linked-confirmation overlap

A subsequent read-only VPS check used `apply_sequence_contract` and the actual
`backtest.confirmed_setup_family` gate on UTC-year-2025 directional candidates.
It verified the linked-output lock before/after and wrote no files or trades.

| Contract | Score-candidate rows | Long reversal | Short reversal | Long continuation | Short continuation |
| --- | ---: | ---: | ---: | ---: | ---: |
| NMZ24 | 0 | 0 | 0 | 0 | 0 |
| NMH25 | 210 | 2 | 1 | 0 | 0 |
| NMM25 | 195 | 2 | 2 | 0 | 1 |
| NMU25 | 191 | 0 | 1 | 0 | 1 |
| NMZ25 | 217 | 1 | 0 | 1 | 1 |
| NMH26 | 33 | 0 | 0 | 2 | 0 |
| Total | 846 | 5 | 4 | 3 | 3 |

The 15 eligible directional signals still require v2 structural risk, objectives,
obstacles, timing/fill-window and market-state checks. They are not accepted
plans, realized trades, P&L or independent validation. The next bounded diagnostic
should evaluate these 15 signals through the shared market-execution decision
API using completed same-contract prefixes and only the observed next open.
Do not change thresholds to increase this sample or repeat the completed builds.
