# Completed-bar chronology v2

`fvg_chronology_v2` is a separate opt-in contract. It preserves every original
feature column, scoring, v1 linkage, legacy execution and production defaults.
The user delegated implementation choices. These choices are conservative
operational definitions based on the supplied sources, not claims that the
sources specify these exact bar counts or swing references.

The NotebookLM source describes a liquidity sweep followed by displacement/MSS
and a retracement to the resulting FVG. The supplied strategy's continuation
section describes a wide-range break, a pullback that holds and a bullish
micro-BOS back in the trend direction. `instructions.md` also requires a hold
beyond the broken level before the pullback and a continuation confirmation.

## Explicit selected semantics

- Reversal: the opposite-side raw sweep must occur on an earlier completed
  one-minute bar than displacement. MSS may occur on the displacement bar,
  because its completed directional close can establish both. An FVG created
  on/after core completion must have its own strictly later retest hold.
- Continuation: freeze the confirmed internal swing broken by the displacement
  event. Require a later completed close beyond that price and the existing
  structure break buffer before the linked FVG retest. The retest must still
  close beyond the original broken price. Freeze the directional confirmed
  internal swing available at that retest, then require a strictly later close
  beyond it and the existing buffer. A swing already broken on the retest bar
  cannot prove post-retest ordering. Missing swing evidence fails closed.
- The original ten-bar lifetime starts at core completion for FVG linkage,
  and at the break for continuation. Core sweep context independently expires
  after ten bars. A new sweep/break resets its association. Missing minutes,
  incomplete bars, loss of the held broken level or gap invalidation prevent
  subsequent continuation confirmation. FVG invalidation clears linked context.
- Entry remains the immediate next-minute open after the final confirmation,
  with existing adverse slippage, risk cap, obstacles and liquidity targets.
  The later continuation confirmation must itself meet the unchanged score
  eligibility and fill-window requirements; the earlier retest's score is not
  carried forward. No research results influenced these definitions.

Only completed start-labelled one-minute inputs with `available_at = timestamp
+ 1 minute` are supported. Raw sweep events are required; recent rolling sweep
context cannot stand in for a new initiating event. Lifecycle creation/retest
identity checks remain those of the separately tested object-linked contract.

Activation requires both `backtest.sequence_contract: fvg_chronology_v2` and
`backtest.execution_model: market_after_retest_confirmation_v2`. The real public
market-execution planner and backtester require matching versioned evidence.
There is no fallback to v1 or the production aggregate booleans. Separate linked
acceptance/retest timestamps and frozen micro-BOS levels expose continuation
evidence. The old production zone planner/alerts are not migrated.

## Local proof and remaining boundary

Both directions/families have accepted planner/backtest fixtures with exact
decision JSON parity and next-open timing. Rejections cover same-bar sweep,
missing hold, retest-bar BOS, later movement of the live swing, invalidation,
expiry, incomplete bars and missing-minute bridges. Prefix/future invariance,
new-trigger resets, old-mode parity and malformed evidence are covered.

Synthetic accepted fixtures establish executable implementation, not historical
performance. The historical v1 diagnostic's zero accepted plans cannot clear
historical accepted-path fidelity for this new contract. A separate locked v2
derivation and decision report on preserved historical inputs remain required.
Do not repeat the upstream feature build, overwrite old outputs, tune scores,
claim full IFVG/structural-level-only entry coverage, or resume R7 yet.

Local chronology checkpoint: **770 passed, 784 reported compatibility warnings
in 20.40 seconds**. The full-suite provenance fixture now snapshots actual tested
producer code into real Git blobs through a private index; it no longer claims
that dirty source bytes came from the prior HEAD. Source/output-lock verification
and deliberate drift failures remain real and unchanged.

## Separate artifact derivation

The existing runner now accepts `--sequence-contract fvg_chronology_v2`.
It reads the completed isolated source build, validates the original locks
against their producer Git blobs, validates lifecycle identity/geometry/events,
and writes new features and input/output locks to a fresh sibling directory.
The frozen strategy's structure buffer and the explicit ten-bar lifetime are
included in the effective derivation identity. The default CLI still derives v1.

Both modes are tested through actual two-contract raw-to-feature stages,
derivation, both independent lock checks, exact original-column equality and
output-drift rejection. An unknown contract is rejected before any output write.
This runner does not repeat the upstream pipeline on VPS, simulate trades, or
certify historical eligibility. Its v2 completion marker is `CHRONOLOGY
DERIVATION: completed; original inputs unchanged; research readiness pending`.

Runner checkpoint: **772 passed, 800 compatibility warnings in 22.03 seconds**.
Both v1 and v2 derivation integration cases passed with preserved source bytes.
