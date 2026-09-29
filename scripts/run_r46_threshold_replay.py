#!/usr/bin/env python3
"""R4.6 true threshold replay from archived precomputed features.

Retain original setup eligibility and additionally require directional
raw_score >= threshold. Re-simulate the *entire chronological bar sequence*
with run_backtest, rather than filtering already executed trades. Threshold
70 must match the frozen R4.5 checkpoint trade-for-trade before proceeding.
No original historical files or production strategy configuration are changed.
"""
from __future__ import annotations

import argparse
import gc
from io import StringIO
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.resume_r45 import (
    CANDIDATE_WEIGHTS, FEATURES, MODELS, YEARS,
    load_config, model_config, read_trades, safe_metrics,
)
from scripts.run_r45_chunked import parquet_replay
from backtest import run_backtest


def apply_threshold(scored: pd.DataFrame, threshold: float) -> pd.DataFrame:
    if not 0 <= threshold <= 100:
        raise ValueError("Threshold must lie between 0 and 100")
    # Copy just the compact, already-scored chronological projection.
    data = scored.copy()
    for side in ("long", "short"):
        candidate = f"{side}_candidate"
        raw = f"{side}_raw_score"
        if candidate not in data or raw not in data:
            raise ValueError(f"Missing directional fields: {candidate}, {raw}")
        score = pd.to_numeric(data[raw], errors="raise")
        data[candidate] = (
            data[candidate].fillna(False).astype(bool)
            & score.ge(threshold)
            & score.notna()
        )
    return data


def assert_frozen_70(actual: pd.DataFrame, frozen: pd.DataFrame) -> None:
    # New row order and trade IDs would indicate path dependence changed.
    # Never run exploratory thresholds until the score-70 replay matches.
    if len(actual) != len(frozen):
        raise AssertionError(
            f"Frozen threshold-70 parity failed: {len(actual)} vs "
            f"{len(frozen)} trades"
        )
    if actual.empty:
        if not frozen.empty:
            raise AssertionError("Frozen 70 parity failed on empty actual")
        return
    if set(actual.columns) != set(frozen.columns):
        raise AssertionError(
            "Frozen 70 parity failed: trade ledger columns differ "
            f"(new={set(actual)-set(frozen)}, missing={set(frozen)-set(actual)})"
        )

    # The frozen reference was loaded from CSV.
    # Normalize the newly generated ledger using exactly the
    # same CSV serialization and parsing representation.
    #
    # Preserve every column, row order, trade ID and numeric
    # comparison. Do not discard genuine execution differences.

    buffer = StringIO()

    actual.reset_index(drop=True)[frozen.columns].to_csv(
        buffer,
        index=False,
    )

    buffer.seek(0)
    comparable_actual = pd.read_csv(buffer)

    pd.testing.assert_frame_equal(
        comparable_actual,
        frozen.reset_index(drop=True),
        check_dtype=False,
        check_exact=False,
        rtol=1e-10,
        atol=1e-10,
    )


def replay(year: int, model: str, thresholds: tuple[int, ...],
           batch_rows: int, root: Path, out: Path):
    frozen_path = root / str(year) / model / "trades.csv"
    if not frozen_path.is_file():
        raise FileNotFoundError(frozen_path)
    config = model_config(
        load_config(Path("config/strategy.yaml")),
        CANDIDATE_WEIGHTS[model],
    )
    scored = parquet_replay(FEATURES[year], config, batch_rows)
    frozen = read_trades(frozen_path)
    print(f"===== PARITY GATE: {year}/{model} threshold 70 =====", flush=True)
    baseline70 = run_backtest(apply_threshold(scored, 70), config)
    assert_frozen_70(baseline70, frozen)
    print(f"EXACT FROZEN 70 PARITY PASSED: {len(frozen)} trades", flush=True)

    summary = []
    for threshold in sorted(set((70, *thresholds))):
        trades = (
            baseline70 if threshold == 70
            else run_backtest(apply_threshold(scored, threshold), config)
        )
        metrics = safe_metrics(trades)
        target = out / str(year) / model / f"threshold_{threshold}"
        target.mkdir(parents=True, exist_ok=True)
        trades.to_csv(target / "trades.csv", index=False)
        (target / "metrics.json").write_text(
            pd.Series(metrics).to_json(indent=2) + "\n"
        )
        net_points = (
            float(trades["net_result_points"].sum())
            if not trades.empty else 0.0
        )
        summary.append({
            "research_year": year, "model": model,
            "threshold": threshold, "trades": len(trades),
            "net_points": round(net_points, 2),
            "expectancy_points": (
                float(trades["net_result_points"].mean())
                if not trades.empty else None
            ),
            "stop_hit_rate": (
                float(trades["stop_hit"].astype(bool).mean())
                if not trades.empty else None
            ),
            "profit_factor": metrics.get("profit_factor"),
        })
        print(
            f"REPLAY {year}/{model} threshold={threshold}: "
            f"{len(trades)} trades, net={net_points:.2f}", flush=True
        )
    pd.DataFrame(summary).to_csv(
        out / f"replay_{year}_{model}_summary.csv", index=False
    )
    del scored
    gc.collect()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--year", required=True, type=int, choices=YEARS)
    p.add_argument("--model", required=True, choices=MODELS)
    p.add_argument("--thresholds", default="75,80,85")
    p.add_argument("--batch-rows", type=int, default=5000)
    p.add_argument(
        "--archive", type=Path, default=Path("research-archive/R4-05")
    )
    p.add_argument(
        "--output-dir", type=Path,
        default=Path("/docker/trade-alerts/data/reports/R4-06_threshold_replay"),
    )
    a = p.parse_args()
    values = tuple(int(item.strip()) for item in a.thresholds.split(","))
    if len(set(values)) != len(values) or not values:
        p.error("Supply unique comma-separated thresholds")
    if not all(70 <= item <= 100 for item in values):
        p.error("Only >=70 thresholds supported by the existing candidate gate")
    if not (100 <= a.batch_rows <= 20000):
        p.error("batch-rows must be 100–20000")
    replay(a.year, a.model, values, a.batch_rows, a.archive, a.output_dir)


if __name__ == "__main__":
    main()
