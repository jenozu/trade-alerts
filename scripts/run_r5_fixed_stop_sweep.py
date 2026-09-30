#!/usr/bin/env python3
"""R5.0 fixed stop-loss sweep with all non-stop behavior frozen.

Research question:
How do fixed 15/20/25/30/35 point stops compare with the untouched current
structural-stop control when the full chronological strategy is replayed?

Only the stop-loss family changes. Entries, scoring, setup qualification,
TP1-TP4, session/time rules, slippage, maximum hold, and one-open-trade
behavior remain unchanged.

The CONTROL model must reproduce the frozen R4.5 baseline ledger trade-for-
trade before any fixed-stop result is trusted.
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
from setup_family_research import derive_setup_family

FIXED_STOPS = (15, 20, 25, 30, 35)


def config_for_fixed_stop(config: dict, stop_points: int) -> dict:
    """Return a copy changing only stop-loss selection to one fixed distance."""
    if stop_points not in FIXED_STOPS:
        raise ValueError(f"Unsupported fixed stop: {stop_points}")

    result = deepcopy(config)
    stop_loss = result["stop_loss"]
    stop_loss["primary_method"] = "fixed"
    stop_loss["preferred_initial_range_points"]["minimum"] = float(stop_points)
    stop_loss["preferred_initial_range_points"]["maximum"] = float(stop_points)
    return result


def max_drawdown_points(trades: pd.DataFrame) -> float:
    if trades.empty:
        return 0.0
    pnl = pd.to_numeric(trades["net_result_points"], errors="raise")
    equity = pd.concat(
        [pd.Series([0.0]), pnl.cumsum().reset_index(drop=True)],
        ignore_index=True,
    )
    peak = equity.cummax()
    return float((peak - equity).max())


def profit_factor(trades: pd.DataFrame) -> float | None:
    if trades.empty:
        return None
    pnl = pd.to_numeric(trades["net_result_points"], errors="raise")
    gross_profit = float(pnl[pnl > 0].sum())
    gross_loss = float(-pnl[pnl < 0].sum())
    return gross_profit / gross_loss if gross_loss > 0 else None


def summarize(year: int, model: str, trades: pd.DataFrame) -> dict:
    metrics = calculate_backtest_metrics(trades)
    pnl = (
        pd.to_numeric(trades["net_result_points"], errors="raise")
        if not trades.empty
        else pd.Series(dtype=float)
    )
    winners = trades.loc[pnl > 0] if len(pnl) else trades.iloc[0:0]
    return {
        "research_year": year,
        "model": model,
        "trades": int(len(trades)),
        "wins": int((pnl > 0).sum()) if len(pnl) else 0,
        "win_rate": float((pnl > 0).mean()) if len(pnl) else None,
        "net_points": float(pnl.sum()) if len(pnl) else 0.0,
        "expectancy_points": float(pnl.mean()) if len(pnl) else None,
        "expectancy_r": metrics.get("expectancy_r"),
        "profit_factor": profit_factor(trades),
        "max_drawdown_points": max_drawdown_points(trades),
        "average_mae_points": metrics.get("average_mae_points"),
        "median_mae_points": (
            float(pd.to_numeric(trades["mae_points"], errors="raise").median())
            if not trades.empty else None
        ),
        "winner_average_mae_points": (
            float(pd.to_numeric(winners["mae_points"], errors="raise").mean())
            if not winners.empty else None
        ),
        "winner_median_mae_points": (
            float(pd.to_numeric(winners["mae_points"], errors="raise").median())
            if not winners.empty else None
        ),
        "average_mfe_points": metrics.get("average_mfe_points"),
        "stop_hit_rate": (
            float(trades["stop_hit"].astype(bool).mean())
            if not trades.empty else None
        ),
        "tp4_hit_rate": (
            float(trades["tp4_hit"].astype(bool).mean())
            if not trades.empty else None
        ),
        "average_hold_minutes": metrics.get("average_hold_minutes"),
    }


def winner_survival(control: pd.DataFrame) -> pd.DataFrame:
    """Baseline eventual-winner MAE survival at each candidate fixed stop.

    Strict '<' is intentional: if MAE reaches the stop distance, the
    conservative simulator considers the stop touched.
    """
    if control.empty:
        return pd.DataFrame(
            columns=["stop_points", "baseline_winners", "surviving_winners", "survival_rate"]
        )

    pnl = pd.to_numeric(control["net_result_points"], errors="raise")
    winners = control.loc[pnl > 0].copy()
    mae = pd.to_numeric(winners["mae_points"], errors="raise")
    rows = []
    for stop in FIXED_STOPS:
        survives = mae.lt(float(stop))
        rows.append(
            {
                "stop_points": stop,
                "baseline_winners": int(len(winners)),
                "surviving_winners": int(survives.sum()),
                "survival_rate": float(survives.mean()) if len(winners) else None,
            }
        )
    return pd.DataFrame(rows)


def setup_family_summary(year: int, model: str, trades: pd.DataFrame) -> list[dict]:
    if trades.empty:
        return []
    frame = trades.copy()
    frame["setup_family"] = derive_setup_family(frame)
    rows = []
    for family, group in frame.groupby("setup_family", sort=True):
        row = summarize(year, model, group)
        row["setup_family"] = family
        rows.append(row)
    return rows


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

    scored = parquet_replay(FEATURES[year], base_config, batch_rows)
    frozen = read_trades(frozen_path)

    print(f"===== R5.0 PARITY GATE: {year} / untouched CONTROL =====", flush=True)
    control = run_backtest(scored, base_config)
    assert_frozen_70(control, frozen)
    print(f"EXACT FROZEN CONTROL PARITY PASSED: {len(frozen)} trades", flush=True)

    year_dir = output / str(year)
    control_dir = year_dir / "control"
    control_dir.mkdir(parents=True, exist_ok=True)
    control.to_csv(control_dir / "trades.csv", index=False)

    summaries = [summarize(year, "CONTROL", control)]
    family_rows = setup_family_summary(year, "CONTROL", control)

    survival = winner_survival(control)
    survival.to_csv(year_dir / "baseline_winner_survival.csv", index=False)

    for stop in FIXED_STOPS:
        config = config_for_fixed_stop(base_config, stop)
        trades = run_backtest(scored, config)

        model = f"FIXED_{stop}"
        target = year_dir / f"fixed_{stop}"
        target.mkdir(parents=True, exist_ok=True)
        trades.to_csv(target / "trades.csv", index=False)

        summary = summarize(year, model, trades)
        (target / "metrics.json").write_text(
            json.dumps(summary, indent=2) + "\n",
            encoding="utf-8",
        )
        summaries.append(summary)
        family_rows.extend(setup_family_summary(year, model, trades))

        print(
            f"R5.0 {year} stop={stop}: "
            f"{summary['trades']} trades, "
            f"win={summary['win_rate']:.4f}, "
            f"net={summary['net_points']:.2f}, "
            f"exp={summary['expectancy_points']:.4f}, "
            f"expR={summary['expectancy_r']:.4f}, "
            f"PF={summary['profit_factor']:.4f}, "
            f"DD={summary['max_drawdown_points']:.2f}",
            flush=True,
        )

    pd.DataFrame(summaries).to_csv(output / f"summary_{year}.csv", index=False)
    pd.DataFrame(family_rows).to_csv(
        output / f"setup_family_summary_{year}.csv", index=False
    )
    print(f"Saved R5.0 summaries for {year} under {output}", flush=True)

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
        default=ROOT / "data/reports/R5_fixed_stop_sweep",
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
