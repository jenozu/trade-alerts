# Baseline execution semantics and limitations

Execution input is completed, left-labelled **one-minute** OHLC bars. A signal
enters at the immediately following minute's open; a missing next minute rejects
the entry. This prevents next-session entries from stale signals. All setup
families currently use this same market-after-signal model.

Stops are market stops: an opening print beyond the stop fills at that worse
open, then applies adverse exit slippage. TP4 uses the target price even when
the open is better (conservative limit assumption). The open has known priority
over the subsequent unknown high/low path. With no opening crossing, simultaneous
stop/target touches remain stop-first. TP1–TP3 record touches without closing any
quantity. Exit slippage is also applied to the conservative TP fill.

Timeout excludes bars starting at/after the deadline and uses the previous
observed close. End-of-data closes at the last observed close. Exit timestamps
remain bar labels, not exact fill times. A missing path at the deadline is not
proof an order could have filled at that prior close. The simulator has no
session-close/holiday liquidation policy; `session_date` is descriptive. Gaps
inside a hold remain OHLC observations; no intragap fill path can be established.
Research based on missing/session-boundary paths requires data/VPS verification.

`entry_on_next_bar_open: false` is a legacy research option; it evaluates signal
bar extremes after a close entry and is **not certified** as realistic execution.
The intended configuration uses next-bar entry. Upstream filtering owns the
candidate window; the backtester trusts explicit candidate flags.

Limit/retest orders require a future touch at a specified level; stop/breakout
orders require a trigger crossing; market-after-confirmation orders require a
completed causal confirmation followed by the next open. None is interchangeable.
The baseline does not enforce family-specific retest/MSS chronology, pending-order
expiry, or live planner trigger/entry-zone semantics. See strategy fidelity audit.

Corrected gap fills and stale next-session signal rejection intentionally change
future replay results on affected paths. Frozen archives remain unchanged and
represent the old execution version. Exact new-code parity on real source caches
must be checked on the VPS; a correctness change must never be hidden by replacing
frozen expected outputs. Partial/breakeven models in path_exit_simulator are
separate experimental analyses and are not certified cost-enabled execution.
