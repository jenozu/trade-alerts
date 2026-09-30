#!/usr/bin/env python3
"""R5.1 structural stop-loss sweep with all non-stop behavior frozen.

Models:
- CONTROL: untouched current structural-in-20..25-else-fixed-25 behavior.
- STRUCTURAL_RAW: use the first valid causal internal/external structural stop
  at any positive distance; fall back to fixed 25 only when structure is
  unavailable or invalid.
- STRUCTURAL_CAP_25: use the valid structural stop when risk is <=25 points;
  otherwise fall back to fixed 25.

This experiment isolates the structural-stop family only. Entries, scoring,
setup qualification, targets, session/time rules, slippage, maximum hold, and
one-open-trade behavior remain unchanged.
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
from backtest import run_backtest

MODELS = ("STRUCTURAL_RAW", "STRUCTURAL_CAP_25")


def config_for_structural_model(config: dict, model: str) -> dict:
    if model not in MODELS:
        raise ValueError(f"Unsupported structural stop model: {model}")
    result = deepcopy(config)
    if model == "STRUCTURAL_RAW":
        result["stop_loss"]["primary_method"] = "structural_raw"
    elif model == "STRUCTURAL_CAP_25":
        result["stop_loss"]["primary_method"] = "structural_cap"
        result["stop_loss"]["preferred_initial_range_points"]["maximum"] = 25.0
    return result


def stop_distance_summary(year: int, model: str, trades: pd.DataFrame) -> dict:
    values = pd.to_numeric(trades["stop_distance_points"], errors="raise")
    if values.empty:
        return {
            "research_year": year,
            "model": model,
            "trades": 0,
            "mean_stop_points": None,
            "median_stop_points": None,
            "p10_stop_points": None,
            "p90_stop_points": None,
            "minimum_stop_points": None,
            "maximum_stop_points": None,
            "pct_below_15": None,
            "pct_below_20": None,
            "pct_above_25": None,
            "pct_above_35": None,
        }
    return {
        "research_year": year,
        "model": model,
        "trades": int(len(values)),
        "mean_stop_points": float(values.mean()),
        "median_stop_points": float(values.median()),
        "p10_stop_points": float(values.quantile(0.10)),
        "p90_stop_points": float(values.quantile(0.90)),
        "minimum_stop_points": float(values.min()),
        "maximum_stop_points": float(values.max()),
        "pct_below_15": float(values.lt(15.0).mean()),
        "pct_below_20": float(values.lt(20.0).mean()),
        "pct_above_25": float(values.gt(25.0).mean()),
        "pct_above_35": float(values.gt(35.0).mean()),
    }


def replay_year(year: int, *, batch_rows: int, archive: Path, output: Path) -> None:
    frozen_path = archive / str(year) / "baseline" / "trades.csv"
    if not frozen_path.is_file():
        raise FileNotFoundError(frozen_path)

    base_config = model_config(load_config(Path("config/strategy.yaml")), CANDIDATE_WEIGHTS["baseline"])
    scored = parquet_replay(FEATURES[year], base_config, batch_rows)
    frozen = read_trades(frozen_path)

    print(f"===== R5.1 PARITY GATE: {year} / untouched CONTROL =====", flush=True)
    control = run_backtest(scored, base_config)
    assert_frozen_70(control, frozen)
    print(f"EXACT FROZEN CONTROL PARITY PASSED: {len(frozen)} trades", flush=True)

    year_dir = output / str(year)
    control_dir = year_dir / "control"
    control_dir.mkdir(parents=True, exist_ok=True)
    control.to_csv(control_dir / "trades.csv", index=False)

    summaries = [summarize(year, "CONTROL", control)]
    family_rows = setup_family_summary(year, "CONTROL", control)
    distance_rows = [stop_distance_summary(year, "CONTROL", control)]

    for model in MODELS:
        config = config_for_structural_model(base_config, model)
        trades = run_backtest(scored, config)

        target = year_dir / model.lower()
        target.mkdir(parents=True, exist_ok=True)
        trades.to_csv(target / "trades.csv", index=False)

        summary = summarize(year, model, trades)
        distance = stop_distance_summary(year, model, trades)
        (target / "metrics.json").write_text(
            json.dumps({"performance": summary, "stop_distance": distance}, indent=2) + "\n",
            encoding="utf-8",
        )
        summaries.append(summary)
        distance_rows.append(distance)
        family_rows.extend(setup_family_summary(year, model, trades))

        print(
            f"R5.1 {year} {model}: "
            f"{summary['trades']} trades, "
            f"win={summary['win_rate']:.4f}, "
            f"net={summary['net_points']:.2f}, "
            f"exp={summary['expectancy_points']:.4f}, "
            f"expR={summary['expectancy_r']:.4f}, "
            f"PF={summary['profit_factor']:.4f}, "
            f"DD={summary['max_drawdown_points']:.2f}, "
            f"medianStop={distance['median_stop_points']:.2f}, "
            f"p90Stop={distance['p90_stop_points']:.2f}",
            flush=True,
        )

    pd.DataFrame(summaries).to_csv(output / f"summary_{year}.csv", index=False)
    pd.DataFrame(family_rows).to_csv(output / f"setup_family_summary_{year}.csv", index=False)
    pd.DataFrame(distance_rows).to_csv(output / f"stop_distance_summary_{year}.csv", index=False)
    print(f"Saved R5.1 summaries for {year} under {output}", flush=True)

    del scored
    gc.collect()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", required=True, type=int, choices=YEARS)
    parser.add_argument("--batch-rows", type=int, default=5000)
    parser.add_argument("--archive", type=Path, default=Path("research-archive/R4-05"))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "data/reports/R5_structural_stop_sweep",
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
