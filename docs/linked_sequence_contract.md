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
