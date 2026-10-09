# Confirmed market execution v2

This opt-in integrity version shares the production planner's structural risk,
obstacle and liquidity-objective construction. It is not selected from historical
profitability and does not change score weights or thresholds.

## Decision contract

The selected next-minute-open entry remains. Freeze the completed confirmation
state; the observed immediately following minute open plus adverse slippage is
the execution reference. Do not include that minute's high, low, close or features
in the decision. Check both explicit signal eligibility and fill time within
09:30 inclusive to 10:30 exclusive America/New_York, including DST.

`trade_planner.build_market_execution_plan` is the shared public decision API.
It requires a completed state, directional candidate and fresh entry event for
the selected production family. It calls the existing planner construction with
the market execution reference. Trigger-zone geometry stays recorded as context;
it no longer substitutes for an executed entry when computing risk or distances.
The existing `build_trade_plan` API continues to produce zone-based hypotheses.
It is not an execution decision and should not be compared as if it were a fill.

Use the planner's protected swing and configured structural buffer. Reject missing,
wrong-side or oversized structure; never pull the stop inside invalidation or
substitute a fixed stop. Initial price risk must be positive and no more than
25 points (or the smaller configured preferred maximum). The attached strategy
explicitly says 25-point maximum and to put stops beyond invalidating structure.
Smaller valid structural risk is permitted and retains the planner's downgrade
outside the preferred 20–25 range. Fees and adverse stop gaps can exceed initial
price risk; this is not a guaranteed loss cap.

Use the existing planner's directional objective filtering, minimum room and
reward/risk checks, recalculated relative to executed entry. Levels already passed
in the trade direction are not obstacles ahead. Preserve ranked DOL and liquidity
targets; do not manufacture fixed-distance replacements or round off source levels.
TP1 and TP3 are required by the planner; TP2 is optional. TP4 must exist for the
current full-position runner policy. Missing TP4 means NO TRADE rather than a
silent exit-policy switch. This fail-closed case is reported explicitly and needs
review if an alternative primary-DOL terminal policy is desired later.

Management remains the current configured full-position exit at TP4, structural
stop, 60-minute timeout or end of sample. Earlier targets are observations.
Conservative opening-gap handling, stop-first OHLC ambiguity, commissions and
adverse slippage remain. Only structural-stop invalidation is executable in this
version; other planner invalidation descriptions are retained separately as
planned criteria, not falsely represented as automated exits.

## Boundaries

The old score-only and confirmed-v1 versions and their ledgers remain reproducible.
V2 does not certify upstream sequence-object linkage or same-row reversal order,
introduce EMA/Kumo/SMT/OB requirements, implement partial/breakeven management,
or establish real-data source/rollover parity. These remain independent audit
tasks. No existing cache or archive may be overwritten to adopt this version.

Planner API verification adds 16 positive/rejected cases, including
both families/directions, passing an old obstacle, rejection instead of fixed-stop
fallback, timing/window boundaries and missing runner/evidence. This is synthetic
contract evidence; a new isolated historical replay remains required.

API checkpoint: focused planner suite 26 passed, 5 warnings; full regression
666 passed, 443 warnings in 12.96 seconds. Existing zone-planner contracts remain
green. The backtest integration is a subsequent sequential task.

## Backtest integration

`backtest.execution_model: market_after_retest_confirmation_v2` now calls this
API from a real market-state snapshot containing only the confirmation prefix.
Candidate rejection happens before selecting between eligible long/short scores;
a rejected higher-scoring direction cannot suppress a valid opposite setup.
The ledger stores the complete shared execution decision as `execution_plan`.
The returned dataframe's `execution_decisions` attribute includes rejection
reasons; both cache runners persist it as `execution_decisions.json`, including
when no trade is accepted. This reports evaluated execution candidates, not
every noncandidate bar or a guarantee that every accepted plan became a fill.

The isolated runner accepts repeated `--execution-model` options. Its default
still compares the old score model and confirmed v1. Selected versions are
recorded in the immutable input lock; originals are verified after execution.
V2 refuses fixed-stop, partial/breakeven and target-first configurations,
duplicate timestamps and nonboolean completion/window/candidate metadata.
An absent optional TP2 is stored as missing and cannot count as a touch even
when an opening print crosses TP4.

Integration verification adds 19 cases: real-state price parity for both
directions/families, immutable inputs, risk rejection, future-extreme independence,
completed-trade append invariance, target-gap observations, net costs, opposite
direction eligibility and explicit replay decisions/settings. Focused related
suite: 124 passed, 300 warnings. Full regression: 685 passed, 583 warnings.
Increased warning count comes from exercising existing timedelta paths in the
new fixtures; warnings remain reported compatibility debt.

The production alert adapter still uses zone-based `build_trade_plan` hypotheses.
This change provides the shared execution API; it does not silently migrate
production or certify its future next-open observation/adapter. Real historical
positive/rejected replay evidence and the remaining upstream sequence/rollover
checks are still required before research resumes.

Actual CLI integration from clean local code commit bfdd055 passed for both
the isolated and strict certified cache runners on a synthetic five-bar fixture.
The isolated comparison produced one v1 and one v2 entry, retained the v2
decision, verified both standalone input locks and left every source hash
unchanged. This is tooling evidence, not historical performance or vendor parity.

## Next VPS verification

Use only the existing isolated checkout and sibling venv. Update that checkout
without changing production:

```bash
cd "$HOME/trade-alerts-verify-YwIqEc/repo" &&
git fetch origin research/pre-critical-integrity &&
git merge --ff-only FETCH_HEAD &&
../venv/bin/python -m pytest -q
```

After the tests pass, run the same January sample with both confirmed versions
and a new output directory. This does not generate upstream features or overwrite
the original cache:

```bash
trade_v2_output="$PWD/../replays/january-v2-$(date -u +%Y%m%dT%H%M%SZ)"
../venv/bin/python scripts/run_isolated_cache_replay.py \
  --source-root /docker/trade-alerts \
  --cache-dir /docker/trade-alerts/data/cache/2025_warmup_92d \
  --output-dir "$trade_v2_output" \
  --completed-through 2026-01-02T00:00:00Z \
  --year 2025 \
  --evaluation-start 2025-01-01T00:00:00Z \
  --evaluation-end 2025-02-01T00:00:00Z \
  --execution-model market_after_retest_confirmation_v1 \
  --execution-model market_after_retest_confirmation_v2 \
  --acknowledge-historical-export-assumption &&
../venv/bin/python scripts/lock_experiment_inputs.py \
  --verify "$trade_v2_output/EXPERIMENT_INPUT_LOCK.json" &&
../venv/bin/python - "$trade_v2_output" <<'PY'
import json, sys
from pathlib import Path
folder = Path(sys.argv[1])
summary = json.loads((folder / "REPLAY_SUMMARY.json").read_text())
print("Inputs unchanged:", summary["inputs_unchanged"])
for version, result in summary["results"].items():
    print(version, "trades:", result["trades"])
decisions = json.loads((folder / "market_after_retest_confirmation_v2/execution_decisions.json").read_text())
for item in decisions:
    print(item["signal_time"], item["direction"], item["decision"], item["rejections"])
print("Outputs:", folder)
PY
```

Retain the full decision JSON on the VPS and paste the compact final output.
No download is required. A zero-entry v2 result with documented rejections is
valid diagnostic evidence; do not lower thresholds to manufacture a positive.
