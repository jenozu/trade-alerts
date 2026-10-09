# Selected entry contract — market after retest confirmation v1

Decision date: 2026-10-03. User delegated the limit/retest vs confirmed-market choice.
Selected: **enter at the next one-minute bar open after completed retest confirmation**.
This follows the stated wait-for-confirmation framework and is directly testable
with one-minute OHLC. A resting retest limit could fill before the retest proves
itself; touch/queue/order placement assumptions cannot be established from these
bars. This choice is based on specification and observability, not historical P&L.

## Execution contract

`backtest.execution_model: market_after_retest_confirmation_v1` requires:

1. Existing directional score eligibility, without changing weights or thresholds.
2. Explicit completed-bar and signal-window metadata (new_entry_allowed or
   is_strategy_window). Absence is an error, not assumed permission.
3. Family classification using the same precedence as the live planner: production
   reversal sequence or opposite current/recent sweep means reversal; otherwise
   continuation. A continuation flag cannot override active reversal context.
4. Both the selected family's production sequence and its **fresh entry-valid
   event**, with boolean-typed sequence/event columns. Persistent context alone cannot create repeated entries. If the score
   is ineligible on that event, the old event does not become a later entry.
5. An immediately following one-minute bar. Confirmation cannot be available after
   the proposed fill. available_at is honored when supplied, with a minimum of
   signal timestamp + one minute. Missing next minutes reject stale signals.
6. Fill at that following bar's open plus adverse directional entry slippage.

New-mode ledgers persist execution_model, setup_family and confirmation_time;
signal_time remains the confirmation bar's label. Existing position/commission
accounting and one-open-trade policy remain in effect. Confirmation time is bar
availability, not an invented intrabar touch time. The mode consumes the existing
production flags, without claiming they prove level/object linkage or intrabar
chronology. Those findings remain unresolved in the fidelity audit.

## Versioning and use

`entry_model.fill_mode` records the selected intended fill contract.
`backtest.execution_model: score_signal_v1` explicitly retains the archived
score-only baseline. Omitting execution_model retains that legacy behavior for
old configs and callers. It does **not** approve that baseline for live execution.
This distinction prevents changed strategy semantics from silently rewriting an
old experiment. The new confirmed mode is available for fidelity verification;
no strategy-selection experiment was launched or historical output regenerated.

Use the certified cache runner's explicit override:

```bash
python scripts/run_cached_backtest.py \
  --cache-dir /preserved/cache \
  --input /preserved/raw.parquet \
  --strategy-config /preserved/original-strategy.yaml \
  --execution-model market_after_retest_confirmation_v1 \
  --output-dir /new/versioned/confirmed-replay
```

The original producer config must match the cache certification. The effective
execution override is recorded in the input-lock settings, separately from the
original config hash. Changing descriptive config metadata can change its hash;
never relabel or recertify an old cache to conceal that. Missing production
sequence/event columns require a separately versioned, verified upstream artifact
rather than a silent rebuild/overwrite. Ledger-only analysis still needs no rebuild.

## Remaining fidelity boundaries

This decision resolves **how to fill after retest confirmation**, not the remaining
independent strategy policies. The baseline target/stop calculation still differs
from the live planner; same-row reversal/FVG ordering, exact retest-object linkage,
acceptance/post-retest BOS, risk cap, and signal-time vs fill-time session boundary
need the audit's versioned contract/evidence. Legacy live hypotheses and planner
entry-zone prices are planned levels rather than executed next-open fills. Full
backtest/live execution parity and real-source provenance remain uncertified.

The gate stays PARTIAL/BLOCKED until those issues and the original VPS checks are
resolved. User delegation of this entry choice is recorded; no further confirmation
is needed to use this selected mode in authorized integrity work.
