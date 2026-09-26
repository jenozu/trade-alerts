#!/usr/bin/env python3
"""Resume R4.5 one year/model per process; never recompute a complete checkpoint.

Run workers sequentially from VPS main data using --year and --model. No
market-data API calls or feature rebuilding. --finalize only reads checkpoints,
reconstructs aggregates and verifies each baseline against its frozen ledger.
"""
from __future__ import annotations

import argparse
import gc
import json
import os
from pathlib import Path
import sys
import tempfile

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_r45_full_universe_candidates import (
    load_config, model_config, safe_metrics,
    enrich_scores, run_backtest, calculate_backtest_metrics,
    CANDIDATE_WEIGHTS,
)
from scripts.verify_archive_r45 import (
    MODELS, YEARS, DEFAULT_LEDGERS, FEATURES, DEFAULT_OUTPUT,
    BASELINE_COUNTS, read_trades, trade_fingerprint, audit,
)

def verified_checkpoint(folder: Path) -> tuple[pd.DataFrame, dict] | None:
    csv = folder / "trades.csv"
    metrics_file = folder / "metrics.json"
    if not csv.exists() and not metrics_file.exists():
        return None
    if not csv.is_file() or not metrics_file.is_file():
        raise ValueError(f"Partial checkpoint: {folder}; refusing overwrite")
    trades = read_trades(csv)
    metrics = json.loads(metrics_file.read_text())
    if int(metrics.get("trades", -1)) != len(trades):
        raise ValueError(f"Count mismatch in existing checkpoint: {folder}")
    if len(trades):
        if "net_result_points" not in trades:
            raise ValueError(f"Checkpoint missing net result: {folder}")
        net = pd.to_numeric(trades["net_result_points"], errors="raise").sum()
        if abs(float(net) - float(metrics.get("net_points", float("nan")))) > 0.02:
            raise ValueError(f"Net points mismatch in existing checkpoint: {folder}")
    return trades, metrics


def check_baseline(year: int, trades: pd.DataFrame) -> None:
    control = read_trades(DEFAULT_LEDGERS[year])
    if len(control) != BASELINE_COUNTS[year]:
        raise ValueError(f"Unexpected frozen baseline count for {year}: {len(control)}")
    if trade_fingerprint(control) != trade_fingerprint(trades):
        raise ValueError(
            f"{year} baseline trades differ from frozen historical ledger. "
            "Stop: investigate config/feature parity, do not overwrite existing results."
        )


def atomic_checkpoint(folder: Path, trades: pd.DataFrame, metrics: dict) -> None:
    # Save both payloads off-path and atomically move complete files into place.
    # A crash between moves intentionally leaves a partial checkpoint requiring
    # manual review, never an automatic overwrite.
    folder.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".r45-", dir=folder) as tmp:
        temp = Path(tmp)
        trades.to_csv(temp / "trades.csv", index=False)
        (temp / "metrics.json").write_text(json.dumps(metrics, indent=2, default=str) + "\n")
        os.replace(temp / "trades.csv", folder / "trades.csv")
        os.replace(temp / "metrics.json", folder / "metrics.json")


# These large diagnostic payloads are neither direct scoring inputs nor
# needed by the backtester. Full original Parquet files remain untouched.
# Verified on 10,000 historic candles with exact score and trade parity.
EXCLUDED_DIAGNOSTIC_COLUMNS = frozenset({
    "dol_ranked_candidates",
    "snr_market_state_json",
    "snr_raw_components_json",
    "dol_primary_components",
    "dol_alternate_components",
})


def load_reduced_features(path: Path) -> pd.DataFrame:
    parquet = pq.ParquetFile(path)
    available = parquet.schema_arrow.names
    selected = [name for name in available if name not in EXCLUDED_DIAGNOSTIC_COLUMNS]
    removed = [name for name in available if name in EXCLUDED_DIAGNOSTIC_COLUMNS]
    print(
        f"Selective load: {len(selected)}/{len(available)} columns; "
        f"excluded diagnostic payloads: {removed}", flush=True,
    )
    return pd.read_parquet(path, columns=selected)


def worker(year: int, model: str, out: Path, config_path: Path, features_path: Path) -> None:
    folder = out / str(year) / model
    existing = verified_checkpoint(folder)
    if existing is not None:
        if model == "baseline":
            check_baseline(year, existing[0])
        print(f"SKIP VERIFIED CHECKPOINT {year}/{model}: {len(existing[0])} trades", flush=True)
        return
    if not features_path.is_file():
        raise FileNotFoundError(f"Existing historical features missing: {features_path}")
    print(f"START {year}/{model}: {features_path}", flush=True)
    config = model_config(load_config(config_path), CANDIDATE_WEIGHTS[model])
    features = load_reduced_features(features_path)
    features["timestamp"] = pd.to_datetime(features["timestamp"], utc=True, errors="coerce")
    if features["timestamp"].isna().any():
        raise ValueError("Historical features include invalid timestamps")
    features.sort_values("timestamp", inplace=True)
    features.reset_index(drop=True, inplace=True)
    # enrich_scores already makes its own copy; avoid an additional features.copy().
    scored = enrich_scores(features, config)
    del features
    gc.collect()
    trades = run_backtest(scored, config)
    del scored
    gc.collect()
    metrics = safe_metrics(trades)
    if model == "baseline":
        check_baseline(year, trades)
    atomic_checkpoint(folder, trades, metrics)
    print(f"CHECKPOINT SAVED {year}/{model}: {len(trades)} trades", flush=True)


def finalize(out: Path) -> None:
    # Read-only pass first: do not generate any aggregate if a checkpoint,
    # particularly any historical baseline, is incomplete or inconsistent.
    results = {}
    for year in YEARS:
        results[str(year)] = {}
        for model in MODELS:
            existing = verified_checkpoint(out / str(year) / model)
            if existing is None:
                raise ValueError(f"Missing checkpoint {year}/{model}. Resume only missing workers.")
            trades, metrics = existing
            if model == "baseline":
                check_baseline(year, trades)
            results[str(year)][model] = {
                "weights": CANDIDATE_WEIGHTS[model], "metrics": metrics,
            }
            print(f"VERIFIED {year}/{model}: {len(trades)} trades", flush=True)
    aggregate = {}
    summary = []
    for model in MODELS:
        frames = []
        for year in YEARS:
            trades = read_trades(out / str(year) / model / "trades.csv")
            if len(trades):
                trades["research_year"] = year
                frames.append(trades)
        combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        metrics = calculate_backtest_metrics(combined) if len(combined) else {"trades": 0}
        aggregate[model] = metrics
        summary.append({"model": model, **{
            key: metrics.get(key) for key in (
                "trades", "win_rate", "expectancy_points", "expectancy_r",
                "profit_factor", "net_points", "tp1_hit_rate", "tp2_hit_rate",
                "tp3_hit_rate", "tp4_hit_rate", "stop_rate",
            )
        }})
        combined.to_csv(out / f"{model}_all_years_trades.csv", index=False)
    pd.DataFrame(summary).to_csv(out / "model_summary.csv", index=False)
    (out / "r45_results.json").write_text(
        json.dumps({"years": results, "aggregate": aggregate}, indent=2, default=str) + "\n"
    )
    verification = audit(out, DEFAULT_LEDGERS)
    print("R4.5 complete — all twelve checkpoints verified, frozen baseline parity confirmed.")
    print(json.dumps(verification["aggregate"], indent=2), flush=True)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    task = p.add_mutually_exclusive_group(required=True)
    task.add_argument("--year", type=int, choices=YEARS)
    task.add_argument("--finalize", action="store_true")
    p.add_argument("--model", choices=MODELS, help="Required with --year")
    p.add_argument("--features", type=Path, help="Existing scored Parquet for the selected year")
    p.add_argument("--config", type=Path, default=ROOT / "config/strategy.yaml")
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    a = p.parse_args()
    if a.finalize:
        if a.model is not None or a.features is not None:
            p.error("--model and --features are only valid with --year")
        finalize(a.output_dir)
    else:
        if a.model is None:
            p.error("--model is required with --year")
        worker(a.year, a.model, a.output_dir, a.config, a.features or FEATURES[a.year])


if __name__ == "__main__":
    main()
