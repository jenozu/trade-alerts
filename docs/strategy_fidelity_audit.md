# Strategy fidelity audit — pre-critical checkpoint

## Verdict

**PARTIAL / strategy decisions and VPS verification required.** Causal features
and replay/live feature-state parity are supported by tests. The historical
baseline is **not proven equivalent to the intended retest strategy or the live
planner**. Research selection remains paused. No performance-based rule changes
were made. A passing mismatch test documents a discrepancy; it does not approve it.

Scope: main at 3555c6f, current configs, phases.md, engineering RULES.md, existing
research archives and tests, attached trade strategy / NotebookLM framework / alert
JSON. The Manus audit is supporting evidence, not a new strategy specification.
Earlier framework materials include EMA/Kumo, pivots, optional SMT, OTE and partial
management; current code/config governs implementation status, but cannot resolve
which older discretionary concepts the user still intends as mandatory rules.

## Levels and context

| Concept | Implementation and evidence | Fidelity finding |
|---|---|---|
| PMH/PML | sessions.enrich_with_sessions; config/sessions.yaml; tests/test_sessions.py and test_sessions_contract.py | Premarket 04:00–09:30 ET; developing vs finalized levels causal. Not interchangeable with overnight. |
| PDH/PDL | Prior RTH levels, 09:30–16:00; available next Globex session at 18:00 | Represents prior RTH, not full prior Globex. Real holidays/roll boundary coverage needs verification. |
| ORH/ORL | 5/15/30-minute ORs; finalized at 09:35/09:45/10:00 ET | Levels are context; no independent ORB execution family is implemented. |
| Cash open | rth_open, known after 09:30 minute completes at 09:31 | Completed-bar snapshot cannot use this before 09:31; next-open fill has different timing. |
| Prior swings / internal vs external | swings._pivot_flags/_add_scope; confirmed active internal/external swing levels; liquidity_registry | Mechanical pivot/confirmation and registry rules, not proof of discretionary market-maker strong/weak labels. |
| Weekly extrema | Causal week levels; Sunday 18:00 to Friday 17:00 | Context/targets available; actual stitched coverage needs VPS confirmation. |
| VWAP | vwap.enrich_vwap; volume-weighted cumulative RTH-anchor context | Can supply key-location confluence; no standalone VWAP/cloud reaction entry family. |
| Premium/discount | dealing_range.add_dealing_range using confirmed structural ranges and midpoint; scorer harmonization | Directional confluence, not a universal mandatory pullback gate. |
| PD arrays | fvg/fvg_state and pd_arrays creation/lifecycle, respect/disrespect and inverse context | FVG/IFVG represented. Generic order blocks/OTE/SMT/Ichimoku/EMA discretionary filters are not proved active entry requirements. |
| Pivot / half-back | Session previous-close/half-back and planner level support | Half-back is not a general daily-pivot formula; no such rule was added. |

## Structural definitions and sequence fidelity

| Concept | Current contract | Limitation |
|---|---|---|
| Sweep | liquidity.enrich_liquidity_features: minimum penetration ticks, close back through level when enabled; recent rolling context | Recent context need not be linked to the later FVG's object/level. Directional recent flags contribute to score. |
| Valid break | structure_state distinguishes wick sweep, body-close break and strong displacement break | Not every scored recent BOS/MSS is a validated break/retest entry. |
| Displacement | structure body/ATR/median/close-location filters plus displacement component model (strength/speed/volatility/coverage) | Configured mechanical approximation, not discretionary intent. |
| BOS / MSS / CHOCH | structure.detect_structure_breaks/classify_structure_events and structure_state; confirmed swings and config conditions | Production implementation uses configured close/buffer/scope. A claimed stricter protected-pivot narrative needs explicit definition. |
| FVG | Three-bar gap: current low above high two bars back (bullish), inverse for bearish; configured minimum gap and optional displacement requirement | Current/corresponding-bar displacement convention is code's definition; not automatically the discretionary middle-candle impulse rule. |
| IFVG | pd_arrays/FVG lifecycle inversion on disrespect, with later respect context | Scorer may award IFVG context, but production ordered reversal sequence is built from original FVG flags; IFVG-only alternate entry is not proved. |
| Strong/protected levels | Planner calls nearest_important_swing high/low protected structure | This naming does not establish an independent protected pivot/strong-low algorithm. |
| DOL | dol ranks configured targets using context, direction and distance; planner uses primary/alternate DOL | Baseline records DOL direction but targets fixed price distances, not the DOL pool. |

The production reversal chain uses structure._ordered_core_sequence then
_ordered_fvg_confirmation: sweep → displacement → MSS → FVG → retest. Older
out-of-order events are rejected by existing tests. However, multiple events can
advance on the **same row**, and FVG creation/retest can complete on the same row.
OHLC does not establish that intrabar order; a new audit test exposes this fact.
These booleans also do not link every retest to the initiating break/level/object.

Continuation requires a displacement structure-break event and a **later-bar**
FVG retest hold within lookback (_ordered_continuation_confirmation). It does not
separately require acceptance duration and a new post-retest micro-BOS; planner
criteria infer acceptance from sequence and can reference the original BOS.
Same-bar continuation break/retest is rejected (existing regression tests).

Scorer inputs reward recent sweep, displacement, shift, FVG/retest independently.
Changing only bullish_reversal_sequence leaves score_setup unchanged in the new
fixture. Backtest directional_candidate uses candidate flag/band; it never calls
the production sequence gate. Thus correct ingredients in a wrong chronology can
still qualify for baseline research trades. Altering this gate is a strategy
semantics change requiring a versioned specification, not a P&L optimization.

## Setup families and execution

| Family | Live path | Historical baseline |
|---|---|---|
| Sweep reversal | Planner labels from production reversal sequence or opposite recent sweep; ENTRY VALID requires reversal sequence; live state advances through confirmation/retest states | Family not persisted; research derives reversal from liquidity_sweep. No family-specific entry gate or retest order. |
| Break/retest continuation | Planner requires production continuation sequence for ENTRY VALID; live states include acceptance/retest/micro-BOS | All unswept-context trades are retrospectively labelled continuation even if no valid break/retest occurred. |
| VWAP/structural reaction | Context and trigger zones, not an independent armed family | No independent family; cannot infer activation from feature presence. |
| OR/opening drive | OR context and potential levels | No separate family-specific execution implementation. |

Baseline is next-minute **market after scored signal** with one full-position
exit at TP4/stop/timeout/end-of-data; TP1–3 are observations. The intended materials
ask for retest entries, structure invalidation and liquidity objectives. Live
planner risk_entry_price is the conservative edge of a deterministic trigger
zone, not a simulated fill. No automatic live orders exist. Limit/retest,
stop/breakout and market-after-confirmation models must be specified separately.

Backtest stop uses active internal/external swing plus buffer, falling back to
fixed risk when unavailable or on the wrong side of entry. Planner rejects
missing/invalid/oversized structure and may downgrade risk outside 20–25 points;
maximum allowed planner risk derives from configured research stop values. Neither
path universally enforces the originally stated 25-point maximum. Confirm the
intended cap before changing it. Partial/BE experimental simulators are separate;
current baseline does not represent the older discretionary scaling template.

## Trading window and timestamps

Sessions supplies new_entry_allowed / is_strategy_window for 09:30 inclusive to
10:30 exclusive ET. scorer.entry_window_valid disables out-of-window rows when
flags exist; if both are absent it permissively returns True. Backtester trusts
explicit candidate flags and does not independently enforce the clock. Live
planner may legitimately produce premarket **hypotheses**; that is not an entry.

Eligibility currently references the **signal bar label**, while fill is next bar
open. A 10:29 signal can therefore fill at 10:30 unless an explicit fill-time
policy is selected. Snapshot as_of is completed-bar availability time; signal_time
and exit_time are bar labels. This difference must be normalized in real replay
comparison, not mistaken for future leakage or silently shifted away.

## Deterministic replay evidence

New tests/test_strategy_fidelity.py supplies:

- a fixed positive planner/backtest fixture: direction, score (82), DOL, entry
  (100) and structural stop (78) agree; planner remains HYPOTHESIS while baseline
  enters. TP1 differs (130 vs 125), TP4 differs (180 vs 200). Baseline lacks explicit
  family, confirmation and invalidation fields. This is a demonstrated mismatch;
- a 90-bar deterministic synthetic 2025 fixture through real production stages:
  resample → bias → sessions → VWAP → volume → SNR → swings → liquidity → FVG →
  PD arrays → structure → dealing range → DOL → scorer → market state → planner
  → alert. A completed 60-bar prefix gives identical state/plan/alert and visible
  backtest results to full-history replay at the same as_of. No stages are stubbed;
- score/sequence and window-policy regression findings;
- same-row ordering ambiguity and artificial contract-gap FVG tests.

This proves local deterministic pipeline integration and append invariance on the
synthetic fixture, **not real-data positive-entry planner/backtest parity**. Existing
replay_parity, structure, live_setup_state, market_state, trade_planner and rollover
fixtures remain intact. For VPS replays compare signal bar timestamp and available_at,
direction, explicitly defined family, score, DOL, confirmation, actual entry/zone,
stop, all targets and invalidation. Do not invent absent baseline fields.

## Futures-data sanity

rollover.stitch_contract_frames uses explicit contract windows, unadjusted raw
prices, inclusive new-contract start/exclusive old-contract end, and contract /
rollover_segment / rollover_boundary metadata. run_rollover_pipeline explicitly
splits segments and runs independent feature pipelines/backtests. This avoids
cross-contract rolling features/FVGs on that path; trades close at segment end.
The direct run_pipeline and cache paths do not themselves establish that the
input was segmented. The artificial gap fixture demonstrates that concatenating
contracts without segmentation can create false FVGs, while isolated segments do
not. ATR/displacement/structure and session extrema may likewise be affected if
unadjusted contract boundaries are bridged; actual incidence is not established.

Barchart tooling audits manifests and analyzes volume crossover (including
unconfirmed fallback labels). The tracked R4.5 verification manifest proves ledger
hashes/counts/parity, not the full raw-candle roll schedule or vendor adjustment
method. No raw historical VPS dataset is present here. Therefore verify on VPS:

1. Exact contracts/IDs, source hashes and vendor continuous/back-adjustment status
   for each preserved year cache, including warmup vs research-year coverage.
2. Applied roll windows/method, roll gap sizes and old/new volume around crossover;
   fallback cases must remain flagged rather than treated as validated volume rolls.
3. Whether feature caches came from segmented rollover pipeline or unsegmented
   input; verify FVG/displacement/MSS do not bridge segment boundaries.
4. PMH/PML/PDH/PDL availability and same-contract coverage at roll starts; segment
   resets may remove prior-day context until sufficient new-contract history exists.
5. Real-cache replay impact from corrected stop gaps and rejected stale entries.

Existing archives remain unchanged. Their analyses remain reproducible using old
recorded execution versions and preserved ledgers; corrected-code regeneration
requires original inputs. No blanket historical corruption claim is justified.

## Decisions needed to finish the gate

Adopt a written execution contract: mandatory ordered retest/confirmation vs
score-only research baseline; limit/retest or confirmed-market fill; signal-time
vs fill-time entry window; family/level/object linkage, acceptance and post-retest
BOS; same-row reversal/FVG allowance; actual risk cap and target/management policy.
Then implement the versioned semantics with positive-entry historical parity
fixtures, establish a forward model freeze and complete the listed VPS checks.
The smallest safe work here is the test/audit framework; guessing these choices
would change strategy-significant trades contrary to RULES.md section 6.


## Entry decision follow-up — 2026-10-03

The user delegated the entry-method decision. Selected and implemented:
market_after_retest_confirmation_v1, a next-minute-open fill after a fresh
completed production retest-confirmation event. See
[confirmed entry contract](confirmed_entry_execution.md). The planner and this
mode now share family precedence; legacy score_signal_v1 remains explicit for
old baseline reproduction. New mode records family, confirmation time and
execution version and rejects missing confirmation schema or late availability.

This resolves the limit-vs-market choice. The audit's baseline findings above
remain historically valid, and remaining target/stop, raw chronology and actual
VPS parity findings are not reclassified PASS. No research selection ran.

## Isolated historical replay evidence — 2026-10-05

User-run VPS verification of the review checkout reported 650 passing tests.
The frozen January 2025 replay reported unchanged inputs, 36 legacy entries
and one confirmed-market entry. These are diagnostic counts, not evidence of
performance or completion of the research gate. This evidence was supplied as
terminal output/screenshots; the historical input files are not available in
the local development checkout.

The confirmed short used the completed 2025-01-29 15:14 UTC signal, available
at 15:15 UTC, and the next-minute raw open of 21536.5. Adverse entry slippage
gave 21536.25; the backtest used a 25-point stop at 21561.25 and fixed targets.
The ledger reported a holding-time exit, target-one through target-three
touches and zero commission. Target touches are not partial exits.

Building the production market state at the same 15:15 UTC cutoff and calling
the planner with the locked producer strategy returned NO TRADE. Its short
rejection was insufficient_room_to_first_obstacle:7.00<25.00. A subsequent
read-only diagnostic identified these planner references:

| Reference | Price | Distance below planner risk entry |
| --- | ---: | ---: |
| Conservative short trigger-zone edge | 21560.25 | 0 |
| Asia-session low | 21553.25 | 7.00 |
| Nearest equal low | 21535.50 | 24.75 |
| Opposing confluence zone | 21534.875 | 25.375 |

The protected swing high was 21561.0. The planner's 7-point calculation uses
its trigger-zone edge, not the confirmed-market fill. The Asia low is already
above the backtest short entry; copying that rejection verbatim into a market
entry simulation would mix entry references. Likewise, the planner swing
reference does not establish equivalence with the backtest fixed-distance stop.

This is a demonstrated historical planner/backtest decision mismatch. Shared
family precedence and causal next-minute timing do not establish full strategy
parity. The next implementation must specify and test market-entry-relative
obstacle eligibility, structural stop construction and target/management rules
under the versioned execution contract. Do not lower thresholds to admit this
example or classify the remaining fidelity gate as passed. Production and
historical archive files were not modified by these diagnostics.
