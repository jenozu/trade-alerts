#!/usr/bin/env python3
"""Memory-bounded R4.5 score replay; backtest once on the full chronological year.

Source features are previously calculated, not regenerated. Scoring is strictly
per-row in scorer.enrich_scores; batches don't reset any rolling indicator
because all market-state and feature columns are precomputed in the Parquet.
The complete, thin scored sequence is concatenated before the unchanged
run_backtest call, preserving open-trade and next-bar behavior at boundaries.

Runs must reproduce the original frozen baseline. Do not use this script
to publish candidate comparisons without all model-year parity checks.
"""
from __future__ import annotations

import argparse
import gc
import os
from pathlib import Path
import sys

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.resume_r45 import (
    CANDIDATE_WEIGHTS, FEATURES, MODELS, YEARS, DEFAULT_OUTPUT,
    EXCLUDED_DIAGNOSTIC_COLUMNS, atomic_checkpoint, check_baseline,
    load_config, model_config, safe_metrics, verified_checkpoint,
)
from src.scorer import enrich_scores
from src.backtest import run_backtest

# Full set of original source columns used by run_backtest/simulate_trade
# for signal selection, stops, execution and trade-ledger annotations.
BACKTEST_SOURCE_COLUMNS = (
    "timestamp", "open", "high", "low", "close", "session_date",
    "bar_complete", "is_complete",
    "active_internal_swing_low", "active_external_swing_low",
    "active_internal_swing_high", "active_external_swing_high",
    "recent_sell_side_sweep", "recent_buy_side_sweep",
    "recent_bullish_displacement", "recent_bearish_displacement",
    "recent_bullish_mss", "recent_bearish_mss",
    "recent_bullish_bos", "recent_bearish_bos",
    "bullish_fvg_retest_hold", "bearish_fvg_retest_hold",
    "bullish_core_plus_fvg", "bearish_core_plus_fvg",
    "snr_1m", "snr_5m", "snr_15m", "snr_alignment",
    "rvol_rolling", "rvol_time_of_day", "htf_bias", "dol_direction",
)
# Backtest uses these recalculated fields; it does not access auxiliary score
# contribution columns or the original 569-column market-state dataframe.
SCORE_COLUMNS = (
    "long_raw_score", "short_raw_score",
    "long_score_band", "short_score_band",
    "long_candidate", "short_candidate", "score_edge",
)


def scored_backtest_projection(scored: pd.DataFrame) -> pd.DataFrame:
    # Preserve original columns and values where applicable, including
    # optional fields that are absent from some historical archives.
    columns = [
        c for c in (*BACKTEST_SOURCE_COLUMNS, *SCORE_COLUMNS)
        if c in scored.columns
    ]
    return scored.loc[:, columns].copy()


def replay_chunks(
    batches, config: dict, *, output_progress: bool = True,
) -> pd.DataFrame:
    """Score historical input batches, retain only backtest-relevant outputs."""
    projected = []
    last_timestamp = None
    schema = None
    total = 0
    for number, batch in enumerate(batches, start=1):
        features = batch if isinstance(batch, pd.DataFrame) else batch.to_pandas()
        features["timestamp"] = pd.to_datetime(
            features["timestamp"], utc=True, errors="coerce",
        )
        if features["timestamp"].isna().any():
            raise ValueError(f"Chunk {number} contains invalid timestamps")
        if not features["timestamp"].is_monotonic_increasing:
            raise ValueError(
                f"Historical file not sorted by timestamp in chunk {number}; "
                "global sorting needed; refusing non-equivalent chunk replay"
            )
        if last_timestamp is not None and features["timestamp"].iloc[0] < last_timestamp:
            raise ValueError("Historical file out of chronological order across batches")
        last_timestamp = features["timestamp"].iloc[-1]
        scored = enrich_scores(features, config)
        del features
        slim = scored_backtest_projection(scored)
        if schema is None:
            schema = list(slim.columns)
        elif list(slim.columns) != schema:
            raise ValueError("Historical chunk output schema changed; cannot safely concatenate")
        projected.append(slim)
        total += len(slim)
        del scored, slim, batch
        gc.collect()
        if output_progress:
            print(f"SCORED {total:,} candles across {number} batches", flush=True)
    if not projected:
        raise ValueError("No historical rows supplied")
    result = pd.concat(projected, ignore_index=True)
    del projected
    gc.collect()
    return result


def parquet_replay(path: Path, config: dict, batch_rows: int) -> pd.DataFrame:
    parquet = pq.ParquetFile(path)
    all_columns = parquet.schema_arrow.names
    selected = [
        name for name in all_columns
        if name not in EXCLUDED_DIAGNOSTIC_COLUMNS
    ]
    print(
        f"Reading {parquet.metadata.num_rows:,} existing rows, "
        f"{len(selected)}/{len(all_columns)} columns in batches of {batch_rows:,}",
        flush=True,
    )
    return replay_chunks(
        parquet.iter_batches(batch_size=batch_rows, columns=selected),
        config,
    )


def worker(year: int, model: str, output: Path, config_path: Path,
           features_path: Path, batch_rows: int) -> None:
    folder = output / str(year) / model
    existing = verified_checkpoint(folder)
    if existing is not None:
        if model == "baseline":
            check_baseline(year, existing[0])
        print(f"SKIP VERIFIED CHECKPOINT {year}/{model}: {len(existing[0])} trades")
        return
    if not features_path.is_file():
        raise FileNotFoundError(features_path)
    cfg = model_config(load_config(config_path), CANDIDATE_WEIGHTS[model])
    print(f"START CHUNKED {year}/{model}", flush=True)
    thin = parquet_replay(features_path, cfg, batch_rows)
    print(
        f"COMPLETE CHRONOLOGICAL BACKTEST INPUT: {len(thin):,} rows, "
        f"{thin.memory_usage(deep=True).sum() / 1048576:.1f} MiB",
        flush=True,
    )
    trades = run_backtest(thin, cfg)
    del thin
    gc.collect()
    if model == "baseline":
        check_baseline(year, trades)
    metrics = safe_metrics(trades)
    atomic_checkpoint(folder, trades, metrics)
    print(f"CHECKPOINT SAVED {year}/{model}: {len(trades)} trades", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, choices=YEARS, required=True)
    parser.add_argument("--model", choices=MODELS, required=True)
    parser.add_argument("--features", type=Path)
    parser.add_argument("--config", type=Path, default=ROOT / "config/strategy.yaml")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--batch-rows", type=int, default=5000)
    a = parser.parse_args()
    if not 100 <= a.batch_rows <= 20000:
        parser.error("batch rows must be between 100 and 20000")
    worker(
        a.year, a.model, a.output_dir, a.config,
        a.features or FEATURES[a.year], a.batch_rows,
    )


if __name__ == "__main__":
    main()
