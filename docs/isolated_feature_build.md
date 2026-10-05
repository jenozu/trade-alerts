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
the committed command path. The historical VPS build has now completed; see
the evidence below. Do not rerun this build for the current checkpoint.

## Completed VPS command (reference only)

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

## Historical completion and availability review — 2026-10-05

User-supplied terminal evidence records the successful build at
`/root/trade-alerts-verify-YwIqEc/replays/full-2025-isolated-features-20261005T185645Z`.
All six segments passed raw identity, same-contract ATR, checked initial resets,
raw availability preservation and non-future context checks. Inputs remained
unchanged. Both persisted locks independently returned VERIFIED afterward.
The VPS builder test file passed nine tests with 21 reported warnings.

| Contract | Source rows | 2025 score candidates | Candidates missing PDH/PDL | Candidates missing daily availability |
| --- | ---: | ---: | ---: | ---: |
| NMZ24 | 75,315 | 0 | 0 | 0 |
| NMH25 | 85,772 | 210 | 7 | 0 |
| NMM25 | 86,668 | 195 | 2 | 2 |
| NMU25 | 89,715 | 191 | 3 | 3 |
| NMZ25 | 88,590 | 217 | 4 | 4 |
| NMH26 | 14,955 | 33 | 4 | 4 |
| Total | 441,015 | 846 | 20 | 13 |

2025 contains 352,125 rows by UTC timestamp year. Every score candidate has
ATR and 15m/30m/1h/4h availability. Each segment's first 13 ATR rows are warmup.
Daily bias is explicitly context-only in configuration; missing daily context
alone does not establish a defective entry or authorize a new veto.

Of the 20 candidates missing both prior-RTH levels, 19 failed the shared family
confirmation gate. The remaining short continuation was March 18 at 13:38 UTC
(09:38 ET). A read-only real v2 backtest on rebuilt NMM25 March 17–18 data
produced zero trades. At 13:39 UTC its entry reference was 19798.5 and its
decision was NO_TRADE, with exact rejections
`structural_risk_too_large:92.00>25.00` and
`tp1_market_objective_unavailable_before_primary_dol`.

This closes that particular candidate diagnostic, not universal warmup eligibility
or positive historical parity. The seven January 10 missing-prior-RTH candidates
still need source coverage classification; do not assume roll warmup, a holiday
or corrupted data. No forward fill or eligibility override was introduced.
Outputs remain FEATURE_CANDIDATE_NOT_RESEARCH_READY pending sequence fidelity
and corrected baseline checks. Historical findings here are transcribed from
user-run terminal evidence; the actual Parquets are not available locally.
