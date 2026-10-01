#!/usr/bin/env python3
"""R5.2 sweep-extreme stop research with all non-stop behavior frozen.

The experiment reconstructs the most recent causal opposite-side liquidity
sweep extreme from the full scored stream:
- LONG -> most recent sell-side sweep bar low
- SHORT -> most recent buy-side sweep bar high

The stop is placed 2 points beyond that extreme, reusing the existing stop
buffer. If no valid recent sweep extreme exists, the untouched fixed-25
fallback is used.

Only stop placement changes. Entries, scoring, setup qualification, TP logic,
session/time rules, slippage, maximum hold, and one-open-trade behavior remain
frozen.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import gc
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.resume_r45 import CANDIDATE_WEIGHTS, FEATURES, YEARS, load_config, model_config, read_trades
from scripts.run_r45_chunked import parquet_replay
from scripts.run_r46_threshold_replay import assert_frozen_70
from scripts.run_r5_fixed_stop_sweep import summarize, setup_family_summary
from scripts.run_r51_structural_stop_sweep import stop_distance_summary
from backtest import run_backtest


def add_recent_sweep_extremes(frame: pd.DataFrame, lookback_bars: int) -> pd.DataFrame:
    """Add causal recent sweep wick extremes using only current/past bars."""
    if lookback_bars < 1:
        raise ValueError("lookback_bars must be >= 1")
    required = {
        "low",
        "high",
        "sell_side_liquidity_sweep",
        "buy_side_liquidity_sweep",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing sweep-extreme columns: {sorted(missing)}")

    result = frame.copy()
    limit = max(0, lookback_bars - 1)

    sell_extreme = result["low"].where(result["sell_side_liquidity_sweep"].fillna(False).astype(bool))
    buy_extreme = result["high"].where(result["buy_side_liquidity_sweep"].fillna(False).astype(bool))

    if limit == 0:
        result["recent_sell_side_sweep_extreme_low"] = sell_extreme
        result["recent_buy_side_sweep_extreme_high"] = buy_extreme
    else:
        result["recent_sell_side_sweep_extreme_low"] = sell_extreme.ffill(limit=limit)
        result["recent_buy_side_sweep_extreme_high"] = buy_extreme.ffill(limit=limit)

    return result


def config_for_sweep_extreme(config: dict) -> dict:
    result = deepcopy(config)
    result["stop_loss"]["primary_method"] = "sweep_extreme"
    return result


def coverage_summary(frame: pd.DataFrame) -> dict:
    return {
        "rows": int(len(frame)),
        "rows_with_recent_sell_sweep_extreme": int(frame["recent_sell_side_sweep_extreme_low"].notna().sum()),
        "rows_with_recent_buy_sweep_extreme": int(frame["recent_buy_side_sweep_extreme_high"].notna().sum()),
    }


def replay_year(year: int, *, batch_rows: int, archive: Path, output: Path) -> None:
    frozen_path = archive / str(year) / "baseline" / "trades.csv"
    if not frozen_path.is_file():
        raise FileNotFoundError(frozen_path)

    base_config = model_config(load_config(Path("config/strategy.yaml")), CANDIDATE_WEIGHTS["baseline"])
    scored = parquet_replay(FEATURES[year], base_config, batch_rows)
    frozen = read_trades(frozen_path)

    print(f"===== R5.2 PARITY GATE: {year} / untouched CONTROL =====", flush=True)
    control = run_backtest(scored, base_config)
    assert_frozen_70(control, frozen)
    print(f"EXACT FROZEN CONTROL PARITY PASSED: {len(frozen)} trades", flush=True)

    lookback = int(base_config.get("liquidity", {}).get("sweep", {}).get("recent_context_bars", 10))
    enriched = add_recent_sweep_extremes(scored, lookback)

    year_dir = output / str(year)
    control_dir = year_dir / "control"
    control_dir.mkdir(parents=True, exist_ok=True)
    control.to_csv(control_dir / "trades.csv", index=False)

    config = config_for_sweep_extreme(base_config)
    trades = run_backtest(enriched, config)

    target = year_dir / "sweep_extreme"
    target.mkdir(parents=True, exist_ok=True)
    trades.to_csv(target / "trades.csv", index=False)

    control_summary = summarize(year, "CONTROL", control)
    sweep_summary = summarize(year, "SWEEP_EXTREME", trades)
    distance = stop_distance_summary(year, "SWEEP_EXTREME", trades)
    coverage = coverage_summary(enriched)

    (target / "metrics.json").write_text(
        json.dumps(
            {
                "performance": sweep_summary,
                "stop_distance": distance,
                "coverage": coverage,
                "lookback_bars": lookback,
                "buffer_points": float(base_config["stop_loss"]["structural"]["buffer_points"]),
            },
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    pd.DataFrame([control_summary, sweep_summary]).to_csv(output / f"summary_{year}.csv", index=False)
    pd.DataFrame(setup_family_summary(year, "CONTROL", control) + setup_family_summary(year, "SWEEP_EXTREME", trades)).to_csv(
        output / f"setup_family_summary_{year}.csv", index=False
    )
    pd.DataFrame([distance]).to_csv(output / f"stop_distance_summary_{year}.csv", index=False)

    print(
        f"R5.2 {year} SWEEP_EXTREME: "
        f"{sweep_summary['trades']} trades, "
        f"win={sweep_summary['win_rate']:.4f}, "
        f"net={sweep_summary['net_points']:.2f}, "
        f"exp={sweep_summary['expectancy_points']:.4f}, "
        f"expR={sweep_summary['expectancy_r']:.4f}, "
        f"PF={sweep_summary['profit_factor']:.4f}, "
        f"DD={sweep_summary['max_drawdown_points']:.2f}, "
        f"medianStop={distance['median_stop_points']:.2f}, "
        f"p90Stop={distance['p90_stop_points']:.2f}",
        flush=True,
    )
    print(f"Saved R5.2 summaries for {year} under {output}", flush=True)

    del scored, enriched
    gc.collect()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", required=True, type=int, choices=YEARS)
    parser.add_argument("--batch-rows", type=int, default=5000)
    parser.add_argument("--archive", type=Path, default=Path("research-archive/R4-05"))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "data/reports/R5_sweep_extreme_stop",
    )
    args = parser.parse_args()

    if not (100 <= args.batch_rows <= 20000):
        parser.error("--batch-rows must be between 100 and 20000")

    replay_year(
        args.year,
        batch_rows=args.batch_rows,
        archive=args.archive,
        output=args.output_dir,
    )


if __name__ == "__main__":
    main()
