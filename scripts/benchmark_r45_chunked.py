#!/usr/bin/env python3
"""Exact real-data parity for small original vs chunked R4.5 scoring + backtest.

This benchmark reads at most --rows existing historical feature rows. It never
writes checkpoints or contacts ProjectX. Do not use its trades as research.
"""
from __future__ import annotations

import argparse
import gc
from itertools import islice
from pathlib import Path
from time import perf_counter

import pandas as pd
import pyarrow.parquet as pq

from run_r45_chunked import (
    EXCLUDED_DIAGNOSTIC_COLUMNS, CANDIDATE_WEIGHTS,
    load_config, model_config, enrich_scores, run_backtest,
    replay_chunks, scored_backtest_projection,
)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--config", type=Path, default=Path("config/strategy.yaml"))
    p.add_argument("--model", choices=list(CANDIDATE_WEIGHTS), default="candidate_conservative")
    p.add_argument("--rows", type=int, default=15000)
    p.add_argument("--batch-rows", type=int, default=5000)
    a = p.parse_args()
    if a.rows < 1 or a.rows > 20000 or a.batch_rows < 1:
        p.error("Use 1–20,000 input rows and a positive chunk size")
    pqfile = pq.ParquetFile(a.input)
    cols = [
        c for c in pqfile.schema_arrow.names
        if c not in EXCLUDED_DIAGNOSTIC_COLUMNS
    ]
    cfg = model_config(load_config(a.config), CANDIDATE_WEIGHTS[a.model])
    print(f"ORIGINAL: {a.rows:,} rows, {len(cols)} columns", flush=True)
    source = next(pqfile.iter_batches(batch_size=a.rows, columns=cols)).to_pandas()
    source["timestamp"] = pd.to_datetime(source["timestamp"], utc=True, errors="coerce")
    source = source.sort_values("timestamp").reset_index(drop=True)
    start = perf_counter()
    full_scores = enrich_scores(source, cfg)
    full_projection = scored_backtest_projection(full_scores)
    original_trades = run_backtest(full_projection, cfg)
    del source, full_scores
    gc.collect()
    print(
        f"ORIGINAL DONE: {time_elapsed(start):.1f}s, {len(original_trades)} sample trades",
        flush=True,
    )
    batches = islice(
        pq.ParquetFile(a.input).iter_batches(batch_size=a.batch_rows, columns=cols),
        (a.rows + a.batch_rows - 1) // a.batch_rows,
    )
    start = perf_counter()
    chunk_projection = replay_chunks(batches, cfg)
    if len(chunk_projection) > a.rows:
        chunk_projection = chunk_projection.iloc[:a.rows].copy()
    # Use a multiple of chunk size in parity checks to avoid scoring extra
    # rows with non-identical source cutoffs in the last partial batch.
    pd.testing.assert_frame_equal(
        full_projection, chunk_projection, check_exact=True,
    )
    chunk_trades = run_backtest(chunk_projection, cfg)
    pd.testing.assert_frame_equal(
        original_trades, chunk_trades, check_exact=True,
    )
    print(f"CHUNKED DONE: {time_elapsed(start):.1f}s", flush=True)
    print(
        f"EXACT REAL-DATA SCORE AND TRADE PARITY PASSED "
        f"({a.rows:,} rows, {len(chunk_trades)} sample trades)",
        flush=True,
    )


def time_elapsed(start):
    return perf_counter() - start


if __name__ == "__main__":
    main()
