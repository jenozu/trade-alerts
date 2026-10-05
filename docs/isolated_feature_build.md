# Full-input contract-isolated feature candidates

The five bounded historical rollover diagnostics passed; do not rerun them.
`scripts/run_isolated_feature_build.py` now prepares the separate full-input
candidate artifacts needed for the next availability/warmup review. It reads
only raw columns from the frozen input, verifies producer blobs and recorded
source/config/control hashes, and uses the same real feature-stage orchestration
that passed the bounded historical checks. It never reads old scored values into
feature generation.

Every source row is retained, including the available pre-2025 history. Original
offset segment IDs and raw prices are preserved. Segments must be chronological,
contiguous and consistent with contract changes/boundary markers. Each contract
runs independently, using all of its available source history. No new contract
inherits the old contract's swings, ATR, FVGs or sequence state. No additional
pre-roll history is fabricated, and an incomplete source fails rather than being
silently filtered.

Each segment contains `raw_segment.parquet`, `features_scored.parquet`, and the
normal intermediate feature outputs under `processed/`. The summary records raw
identity, same-contract ATR, checked initial resets, unchanged raw clock and
non-future bias/structure availability. Warmup context lists missing rows and
first non-null bars for ATR, PDH/PDL and HTF availability. Those are descriptive
counts, not a sufficient strategy warmup policy or universal causality proof.
The runner deliberately does not certify full session coverage/research
eligibility, change entry flags, select thresholds, run backtests or send alerts.

`EXPERIMENT_INPUT_LOCK.json` freezes sources, the contaminated scored control,
configs, current commit, orchestration and all transitive `src/*.py` files.
`FEATURE_OUTPUT_LOCK.json` additionally freezes every persisted raw/feature pair;
it can be independently verified using the existing experiment-identity API.
Both locks are verified before the completion marker. Original inputs are checked
after generation. Output must be a fresh directory separate from production.
No `cache_metadata.json` is written, so an ordinary research-cache loader cannot
mistake these candidates for a certified cache.

Validation: focused/related **48 passed, 43 warnings**; full **717 passed,
621 warnings in 17.09s**. The nine new cases exercise the real stages and output
locks, finite raw data, offset IDs, malformed boundaries/segments, raw clock and
future-context rejection, source preservation, incomplete inputs, overwrite
refusal and generated-output drift detection. Feature stages are not mocked.
Existing NumPy timedelta compatibility warnings remain reported.

The actual CLI from clean committed implementation `d57f451` also passed on a
synthetic two-contract source (90 bars each), and both persisted input/output
locks passed independent verification against the same commit. This establishes
the committed command path, not historical full-input completion. The VPS job
below is still required before reviewing actual warmup evidence.

## VPS step

Update only the verification checkout, run the nine new tests, then start one
finite feature-only build using its sibling virtual environment. The full input
has 441,015 rows across six segments; this job is larger than the bounded checks.
Its retained per-stage files also need more disk space than the small diagnostics.
All output goes under the separate verification tree. `nohup` permits disconnects.

```bash
cd "$HOME/trade-alerts-verify-YwIqEc/repo" &&
git fetch origin research/pre-critical-integrity &&
git merge --ff-only FETCH_HEAD &&
../venv/bin/python -m pytest -q tests/test_isolated_feature_build.py &&
trade_feature_output="$PWD/../replays/full-2025-isolated-features-$(date -u +%Y%m%dT%H%M%SZ)" && {
nohup ../venv/bin/python -u scripts/run_isolated_feature_build.py \
  --source-root /docker/trade-alerts \
  --cache-dir /docker/trade-alerts/data/cache/2025_warmup_92d \
  --output-dir "$trade_feature_output" \
  --year 2025 \
  --completed-through 2026-01-02T00:00:00Z \
  --acknowledge-historical-export-assumption \
  > "$trade_feature_output.log" 2>&1 < /dev/null &
printf 'Started PID %s. Log: %s\n' "$!" "$trade_feature_output.log"
}
```

The success marker is `FEATURE BUILD: all segments passed; inputs unchanged;
research readiness pending`, followed by segment summaries and the output path.
A traceback or missing summary means the task has not completed. Do not launch a
second job while this one is running. Inspect the retained summary/warmup evidence
and locks before preparing a corrected execution baseline; R7 remains paused.
