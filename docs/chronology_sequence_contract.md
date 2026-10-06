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

## Locked execution evidence

`scripts/audit_linked_execution.py` verifies preserved linked-output provenance
using original producer blobs and unchanged data/config files. It verifies
summary coverage and every feature identity, records all effective strategy,
execution, cost and slippage settings, and limits candidate eligibility to the
requested UTC development year while retaining the full context history.

It saves independent shared decisions and, when a plan is accepted, runs the
actual backtester under the same contract. Every executed plan must match its
independent decision exactly. Side ties and one-position policy can prevent an
otherwise accepted standalone decision from executing; counts remain distinct.
No whole-segment simulation is repeated when no plan is accepted. Source bytes
and source locks are verified afterward. New input/output locks cover durable
decisions, any diagnostic ledger, effective config and the summary.

The diagnostic does not certify realistic fees, optimize rules, declare a model
freeze or clear research readiness. Zero simulated trades explicitly means no
accepted historical-path proof. Local tests use real chronology derivation,
planner/backtest execution, locks and drift rejection in both directions/families.

### Next VPS job (one fresh run)

Use the existing verification repo and sibling venv. Pull the review branch,
then derive only new chronology fields from the passed full isolated build and
audit those new outputs. This does not rerun upstream indicators or scoring.
The background job survives a terminal disconnect. A failed derivation stops
the audit; never reuse/overwrite a partially completed output directory.

```bash
cd "$HOME/trade-alerts-verify-YwIqEc/repo" &&
git fetch origin research/pre-critical-integrity &&
git merge --ff-only FETCH_HEAD &&
trade_chronology_job="$PWD/../replays/chronology-2025-$(date -u +%Y%m%dT%H%M%SZ)" && {
nohup bash -c '
  set -e
  ../venv/bin/python -u scripts/derive_linked_sequences.py \
    --source-build "$1" --output-dir "$2/features" \
    --sequence-contract fvg_chronology_v2
  ../venv/bin/python -u scripts/audit_linked_execution.py \
    --source-build "$2/features" --output-dir "$2/execution" --year 2025
' bash \
  "$HOME/trade-alerts-verify-YwIqEc/replays/full-2025-isolated-features-20261005T185645Z" \
  "$trade_chronology_job" > "$trade_chronology_job.log" 2>&1 < /dev/null &
printf 'Started PID %s\nLog: %s\n' "$!" "$trade_chronology_job.log"
}
```

Final success marker: `EXECUTION AUDIT: completed; inputs unchanged; both locks
verified; research readiness pending`. Preserve the printed log/output path.
No focused/full test rerun on VPS is needed before this already-tested diagnostic.

Final local regression: **779 passed, 862 compatibility warnings in 23.24s**.
The seven durable execution-audit tests passed with 67 warnings. Warnings include
NumPy timedelta compatibility debt and DataFrame fragmentation performance
warnings in the real-stage derivation; neither class was suppressed.

Committed CLI `467742c` completed actual v2 derivation and execution audit on the
real-stage two-contract synthetic build (180 retained bars). Both stages reported
unchanged original inputs, and the audit verified both locks. This sample had
zero eligible signals; accepted-path proof comes from the separate both-direction/
family fixtures, not this empty synthetic CLI sample. Historical VPS execution
is still required.

## Historical VPS job completed — 2026-10-06 UTC

User terminal screenshot `image(20261006-034255).png` reports successful chronology
derivation and execution audit on all six segments. Job PID 116602 completed.
Output root: `/root/trade-alerts-verify-YwIqEc/replays/chronology-2025-20261006T033846Z`.
The verification checkout was `8d9eda131283847f167a4c9c45b9ecb55d1d1aca`.

The `fvg_chronology_v2` execution summary reports **7 eligible directional
signals, 0 accepted plans, 0 simulated trades and 0 executed-plan parity checks**.
Derivation reports original inputs unchanged. Audit reports inputs unchanged
and both locks verified. DataFrame-fragmentation warnings were emitted; there
is no traceback in the supplied tail and both success markers are present.
This is user-supplied historical evidence, not a locally reproduced VPS run.

Do not rerun the job or tune thresholds to obtain trades. Next independently
verify the four saved feature/execution locks in the unchanged verification
checkout and inspect the saved per-segment summary and seven rejection decisions.
No further pull is needed for that read-only check. Zero trades does not prove
historical accepted-path parity or realistic-cost performance; R7 remains paused.

### Independent four-lock verification and rejection review

Screenshot `image(20261006-034457).png` independently verifies both feature locks
and both execution locks against the unchanged producer checkout. All seven
eligible signals are reversals (three long, four short); no continuation reaches
score-eligible final confirmation in this diagnostic.

| Contract | Signal UTC | Direction | Structural risk | Other rejection evidence |
| --- | --- | --- | ---: | --- |
| NMH25 | 2025-01-29 15:14 | short | 26.75 > 25 | First obstacle 0.75 < 25; TP1 asymmetry 0.03 < 1 |
| NMH25 | 2025-02-07 15:20 | long | 27.50 > 25 | First obstacle 0.75 < 25; TP1 asymmetry 0.03 < 1 |
| NMM25 | 2025-04-04 13:56 | short | 55.75 > 25 | First obstacle 2.25 < 25; TP1 asymmetry 0.04 < 1 |
| NMM25 | 2025-04-07 13:50 | long | 307.25 > 25 | First obstacle 2.50 < 25; TP1 asymmetry 0.01 < 1; primary DOL asymmetry 0.79 < 1 |
| NMM25 | 2025-05-07 13:30 | short | 46.50 > 25 | First obstacle 0.25 < 25; TP1 asymmetry 0.01 < 1 |
| NMU25 | 2025-06-23 14:29 | short | Not evaluated | Immediate next-open fill at 10:30 ET is outside the fill-entry window |
| NMZ25 | 2025-10-16 13:47 | long | 32.75 > 25 | First obstacle 19.25 < 25; TP1 asymmetry 0.59 < 1 |

Six signals fail the unchanged structural cap; one fails timing before price-risk
planning. The terminal output therefore accounts for all zero accepted plans.
This closes the 2025 diagnostic/lock/rejection task without a replay or tuning.
Next inventory preserved 2023/2024 artifacts and producer metadata read-only;
do not rebuild them merely to inspect provenance. Actual fees and broader
historical accepted-path evidence remain unverified.
