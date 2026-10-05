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
