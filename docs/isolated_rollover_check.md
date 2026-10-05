# Bounded contract-isolation diagnostic

The VPS single-contract pipeline guard passed 697 tests (user-reported). The next
task in the research readiness plan is to establish real raw-to-feature rollover
isolation before rebuilding the affected 2025 baseline. Do not repeat the prior
cache inventory or mixed-contract ATR calculation; those findings are preserved
in `rollover_cache_findings.md`.

`scripts/run_isolated_rollover_check.py` reads the exact frozen cache metadata,
verifies original raw/scored/config hashes and producer blobs, then selects at
most seven calendar days on either side of one actual contract transition.
It regenerates the real feature stages independently for the two selected
contract segments, preserving their original offset segment IDs. It projects
only raw fields, so old precomputed ATR or other features cannot enter generation.
It locks the current commit, orchestration, every `src/*.py` dependency, configs,
historical timing assumption and control artifacts, and verifies the lock again
after generation. Outputs must be fresh and separate from the source tree.

Each segment must preserve raw OHLCV, timestamp and contract identity. Its ATR
must match a same-contract rolling true-range calculation across all selected
bars. First-row swing/FVG/previous-day levels and production sequence state must
reset. Synthetic real-stage integration also compares the generated new-contract
features to a standalone new-contract run, with identical persisted outputs.
The 11 new cases include unsafe output paths, malformed segment metadata and
deliberately corrupt price/ATR/level/sequence evidence. No feature mocks are used.

Validation: related suite **36 passed, 35 warnings**; full regression
**708 passed, 605 warnings in 15.44s**. Additional warnings come from exercising
existing NumPy timedelta paths in the new real-stage fixture. They remain reported.

The actual CLI from clean committed code `73452de` passed on a synthetic
two-contract fixture (90 bars each), with all reset/raw/ATR checks and standalone
input-lock verification. This proves the CLI plumbing; it is not VPS historical
evidence. Historical VPS evidence is now recorded below.

This is deliberately a **cold-start feature diagnostic**. It validates OHLCV,
completion and identity, but does not apply the full research/live session-coverage
eligibility gate, certify vendor corrections, prove all chronology/object linkage,
or provide the full-year warmup. Missing higher-timeframe/session context is
expected and cannot be called research-ready. No state/planner/alert/backtest
stages, parameter selection, cache recertification or production writes occur.
The old cache remains a contaminated control. Even a passing check does not
by itself authorize R7 or a full-year strategy comparison.

## VPS command

After updating the isolated checkout, run the March transition with three calendar
days per side. Store the full log in the new output's sibling path so terminal
disconnects do not lose the command's status. `nohup` runs only this finite job.

```bash
cd "$HOME/trade-alerts-verify-YwIqEc/repo" &&
git fetch origin research/pre-critical-integrity &&
git merge --ff-only FETCH_HEAD &&
trade_roll_output="$PWD/../replays/march-roll-isolation-$(date -u +%Y%m%dT%H%M%SZ)" &&
mkdir -p "$PWD/../replays" && {
nohup ../venv/bin/python -u scripts/run_isolated_rollover_check.py \
  --source-root /docker/trade-alerts \
  --cache-dir /docker/trade-alerts/data/cache/2025_warmup_92d \
  --output-dir "$trade_roll_output" \
  --boundary 2025-03-17T22:00:00Z \
  --days-before 3 --days-after 3 \
  --completed-through 2026-01-02T00:00:00Z \
  --acknowledge-historical-export-assumption \
  > "$trade_roll_output.log" 2>&1 < /dev/null &
printf 'Started PID %s. Log: %s\n' "$!" "$trade_roll_output.log"
}
```

Use the following separate block to find the newest diagnostic log and inspect
progress after any reconnect:

```bash
cd "$HOME/trade-alerts-verify-YwIqEc/repo" &&
trade_roll_log=$(find "$PWD/../replays" -maxdepth 1 -type f \
  -name 'march-roll-isolation-*.log' | sort | tail -n 1) &&
test -n "$trade_roll_log" &&
tail -n 12 "$trade_roll_log"
```

A successful run ends with `ROLLOVER CHECK: diagnostic checks passed; inputs
unchanged`, two contract summaries and the output path. A traceback or missing
summary means the check has not passed. Paste these final lines; no download is
required. Retain the complete diagnostic directory and log for subsequent review.

## Historical VPS completion — 2026-10-05

The March command completed at
`/root/trade-alerts-verify-YwIqEc/replays/march-roll-isolation-20261005T182624Z`.
The remaining four ran sequentially under
`/root/trade-alerts-verify-YwIqEc/replays/remaining-rolls-20261005T183346Z`.
The terminal displayed `ALL FOUR REMAINING ROLLOVER CHECKS PASSED`; subsequent
read-only output of each saved summary confirmed `DIAGNOSTIC_ONLY`, unchanged
inputs and all four checks true for both segments. Evidence is user-supplied VPS
terminal screenshots; full JSONs/locks remain on the VPS, not in this checkout.

| Boundary UTC | Old contract / selected bars | New contract / selected bars |
| --- | --- | --- |
| 2024-12-16 23:00 | NMZ24 / 1,380 | NMH25 / 4,140 |
| 2025-03-17 22:00 | NMH25 / 1,380 | NMM25 / 4,140 |
| 2025-06-16 05:00 | NMM25 / 960 | NMU25 / 4,140 |
| 2025-09-15 22:00 | NMU25 / 1,380 | NMZ25 / 4,140 |
| 2025-12-15 23:00 | NMZ25 / 1,380 | NMH26 / 4,140 |

All ten segments preserved raw identity, matched isolated same-contract ATR,
reset the checked initial levels and reset the checked initial sequence flags.
Each had 13 initial ATR warmup bars. The bounded diagnostic task is complete;
do not repeat these checks. This proves the tested isolation path on these
windows, not universal feature causality or research eligibility. The next task
is a separate full-input feature build preserving all available segment history,
followed by availability/warmup review before any corrected backtest or R7 work.
