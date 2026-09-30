#!/usr/bin/env python3
"""R6.0 fixed full-target sweep with all non-target behavior frozen.

Research question:
Does closing the entire position at 50 or 75 points improve the frozen
baseline compared with the current 100-point TP4 exit?

Only the full-position target distance changes. Baseline score weights,
threshold-70 eligibility, entry logic, stop logic, session rules, slippage,
maximum hold, and one-open-trade behavior remain unchanged.

The 100-point control must reproduce the frozen R4.5 baseline ledger
trade-for-trade before exploratory targets are accepted.
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

from scripts.resume_r45 import (
    CANDIDATE_WEIGHTS,
    FEATURES,
    YEARS,
    load_config,
    model_config,
    read_trades,
)
from scripts.run_r45_chunked import parquet_replay
from scripts.run_r46_threshold_replay import assert_frozen_70
from backtest import calculate_backtest_metrics, run_backtest

TARGETS = (50, 75, 100)


def config_for_full_target(config: dict, full_target: int) -> dict:
    """Return a copy with only the fixed full-position target changed."""
    if full_target not in TARGETS:
        raise ValueError(f"Unsupported full target: {full_target}")

    result = deepcopy(config)
    preferred = result["take_profit"]["preferred_initial"]

    # Preserve the existing milestone ladder where it is below the full exit.
    # The simulator exits only on TP4, so duplicated later milestones simply
    # make TP4 equal the requested full-position exit.
    original = (
        float(preferred["tp1_points"]),
        float(preferred["tp2_points"]),
        float(preferred["tp3_points"]),
    )
    preferred["tp1_points"] = min(original[0], float(full_target))
    preferred["tp2_points"] = min(original[1], float(full_target))
    preferred["tp3_points"] = min(original[2], float(full_target))
    preferred["tp4_points"] = float(full_target)

    return result


def max_drawdown_points(trades: pd.DataFrame) -> float:
    if trades.empty:
        return 0.0
    pnl = pd.to_numeric(trades["net_result_points"], errors="raise")
    equity = pnl.cumsum()
    peak = equity.cummax()
    return float((peak - equity).max())


def summarize(year: int, full_target: int, trades: pd.DataFrame) -> dict:
    metrics = calculate_backtest_metrics(trades)
    pnl = (
        pd.to_numeric(trades["net_result_points"], errors="raise")
        if not trades.empty
        else pd.Series(dtype=float)
    )
    return {
        "research_year": year,
        "full_target_points": full_target,
        "trades": int(len(trades)),
        "wins": int((pnl > 0).sum()) if len(pnl) else 0,
        "win_rate": float((pnl > 0).mean()) if len(pnl) else None,
        "net_points": float(pnl.sum()) if len(pnl) else 0.0,
        "expectancy_points": float(pnl.mean()) if len(pnl) else None,
        "expectancy_r": metrics.get("expectancy_r"),
        "profit_factor": metrics.get("profit_factor"),
        "max_drawdown_points": max_drawdown_points(trades),
        "stop_hit_rate": (
            float(trades["stop_hit"].astype(bool).mean())
            if not trades.empty else None
        ),
        "full_target_exit_rate": (
            float(trades["exit_reason"].eq("tp4").mean())
            if not trades.empty else None
        ),
        "average_mfe_points": metrics.get("average_mfe_points"),
        "average_mae_points": metrics.get("average_mae_points"),
        "average_hold_minutes": metrics.get("average_hold_minutes"),
    }


def replay_year(
    year: int,
    *,
    batch_rows: int,
    archive: Path,
    output: Path,
) -> None:
    frozen_path = archive / str(year) / "baseline" / "trades.csv"
    if not frozen_path.is_file():
        raise FileNotFoundError(frozen_path)

    base_config = model_config(
        load_config(Path("config/strategy.yaml")),
        CANDIDATE_WEIGHTS["baseline"],
    )

    # Score the original full chronological feature stream once.
    scored = parquet_replay(FEATURES[year], base_config, batch_rows)
    frozen = read_trades(frozen_path)

    print(f"===== R6.0 PARITY GATE: {year} / full TP 100 =====", flush=True)
    control_config = config_for_full_target(base_config, 100)
    control = run_backtest(scored, control_config)
    assert_frozen_70(control, frozen)
    print(
        f"EXACT TP100 FROZEN PARITY PASSED: {len(frozen)} trades",
        flush=True,
    )

    rows: list[dict] = []
    for full_target in TARGETS:
        config = config_for_full_target(base_config, full_target)
        trades = control if full_target == 100 else run_backtest(scored, config)

        target_dir = output / str(year) / f"tp_{full_target}"
        target_dir.mkdir(parents=True, exist_ok=True)
        trades.to_csv(target_dir / "trades.csv", index=False)

        summary = summarize(year, full_target, trades)
        (target_dir / "metrics.json").write_text(
            json.dumps(summary, indent=2) + "\n",
            encoding="utf-8",
        )
        rows.append(summary)

        print(
            f"R6.0 {year} TP={full_target}: "
            f"{summary['trades']} trades, "
            f"net={summary['net_points']:.2f}, "
            f"exp={summary['expectancy_points']:.4f}, "
            f"PF={summary['profit_factor']:.4f}, "
            f"DD={summary['max_drawdown_points']:.2f}",
            flush=True,
        )

    summary_frame = pd.DataFrame(rows)
    summary_path = output / f"summary_{year}.csv"
    summary_frame.to_csv(summary_path, index=False)
    print(f"Saved {summary_path}", flush=True)

    del scored
    gc.collect()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", required=True, type=int, choices=YEARS)
    parser.add_argument("--batch-rows", type=int, default=5000)
    parser.add_argument(
        "--archive",
        type=Path,
        default=Path("research-archive/R4-05"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "data/reports/R6_fixed_target_sweep",
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
