# Isolated frozen-cache diagnostic replay

`scripts/run_isolated_cache_replay.py` compares corrected legacy execution and
confirmed retest execution on the same frozen feature rows. It is an execution
diagnostic, not a new selection experiment or certification of today's feature
pipeline. Do not promote a mode based on its P&L.

The runner verifies source/scored/config SHA-256 hashes and scored row count.
Every recorded feature hash must match its blob at the recorded producer Git
commit, available in the test checkout. Differences from today's feature files
are reported, never erased. Current feature generation is not invoked and the
original cache metadata is never recertified or modified. Producer manifests
may omit dependencies; their verification alone does not establish full feature
pipeline provenance or real-data parity.

An explicit historical-export assumption uses the approved AS_OF_CONTRACT:
one-minute UTC timestamps label opens, with availability no earlier than one
minute later. Barchart chart documentation supports start-period labels and
download documentation specifies Chicago time for futures; CSV-specific timing
remains an inference. Frozen downloads are not evidence of original live feed
availability or of an immutable vendor correction history. Existing later
availability and false/unknown completion flags remain restrictive. Naive/null,
duplicate, unordered or off-minute time labels fail closed. The selected sample
must be completed through the caller's timezone-aware cutoff.

Date filters limit Parquet reads and derived writes to a selected UTC sample.
Frozen features retain producer warmup, but backtest positions start/close at
sample boundaries. This is not an exact reproduction of a full-year ledger.
Contract-boundary feature isolation, structural stop/target fidelity and positive
live/planner/backtest parity remain unverified.

Run from a separate clean review checkout and use its separate venv. The output
directory must be fresh and disjoint from the entire production source root.
For the first deterministic sample, use 2025-01-06 through 2025-01-11 UTC, chosen
by calendar rather than performance. Production inputs are read only; derived
scored data, provenance, lock and both ledgers are written under the fresh output.
Original/derived/config/provenance files are locked before simulation and checked
again afterwards. A failure leaves diagnostic partial outputs, never a successful
summary; rerun into another fresh directory.

```bash
../venv/bin/python scripts/run_isolated_cache_replay.py \
  --source-root /docker/trade-alerts \
  --cache-dir /docker/trade-alerts/data/cache/2025_warmup_92d \
  --output-dir ../replays/first-week-2025 \
  --year 2025 \
  --evaluation-start 2025-01-06T00:00:00Z \
  --evaluation-end 2025-01-11T00:00:00Z \
  --completed-through 2026-01-02T00:00:00Z \
  --acknowledge-historical-export-assumption
```

The January 2026 cutoff is a historical-completion assumption for the already
downloaded 2025 snapshot, not proof of data availability on that date. Read
`REPLAY_PROVENANCE.json` and `REPLAY_SUMMARY.json`; successful input verification
does not clear the research/deployment gate. Preserve the output directory and
do not commit the Parquet file to Git.

Sources reviewed 2026-10-04:
- https://www.barchart.com/futures/quotes/%24SPX/technical-chart (intraday chart labels)
- https://www.barchart.com/stocks/quotes/%24MNXR/historical-download (CSV timezone)
