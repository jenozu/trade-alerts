#!/usr/bin/env python3
"""R5.3 ATR / volatility-adjusted stop sweep with all non-stop behavior frozen.

Models:
- CONTROL: untouched current stop logic.
- ATR_1_0: 14-bar 1m ATR x 1.0.
- ATR_1_5: 14-bar 1m ATR x 1.5.
- ATR_2_0: 14-bar 1m ATR x 2.0.

ATR is calculated causally from completed/current historical bars available at
signal close. If ATR is unavailable or invalid, the existing fixed-25 fallback
is used.

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

ATR_MODELS = {
    "ATR_1_0": 1.0,
    "ATR_1_5": 1.5,
    "ATR_2_0": 2.0,
}


def add_atr14(frame: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    if period < 1:
        raise ValueError("period must be >= 1")
    required = {"high", "low", "close"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing ATR columns: {sorted(missing)}")

    result = frame.copy()
    previous_close = pd.to_numeric(result["close"], errors="raise").shift(1)
    high = pd.to_numeric(result["high"], errors="raise")
    low = pd.to_numeric(result["low"], errors="raise")

    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    result["atr_14_points"] = true_range.rolling(
        period,
        min_periods=period,
    ).mean()
    return result


def config_for_atr(config: dict, multiplier: float) -> dict:
    if multiplier not in ATR_MODELS.values():
        raise ValueError(f"Unsupported ATR multiplier: {multiplier}")
    result = deepcopy(config)
    result["stop_loss"]["primary_method"] = "atr"
    result["stop_loss"]["atr"] = {
        "period": 14,
        "multiplier": float(multiplier),
    }
    return result


def replay_year(year: int, *, batch_rows: int, archive: Path, output: Path) -> None:
    frozen_path = archive / str(year) / "baseline" / "trades.csv"
    if not frozen_path.is_file():
        raise FileNotFoundError(frozen_path)

    base_config = model_config(
        load_config(Path("config/strategy.yaml")),
        CANDIDATE_WEIGHTS["baseline"],
    )

    scored = parquet_replay(FEATURES[year], base_config, batch_rows)
    frozen = read_trades(frozen_path)

    print(f"===== R5.3 PARITY GATE: {year} / untouched CONTROL =====", flush=True)
    control = run_backtest(scored, base_config)
    assert_frozen_70(control, frozen)
    print(f"EXACT FROZEN CONTROL PARITY PASSED: {len(frozen)} trades", flush=True)

    enriched = add_atr14(scored, 14)

    year_dir = output / str(year)
    control_dir = year_dir / "control"
    control_dir.mkdir(parents=True, exist_ok=True)
    control.to_csv(control_dir / "trades.csv", index=False)

    summaries = [summarize(year, "CONTROL", control)]
    family_rows = setup_family_summary(year, "CONTROL", control)
    distance_rows = []

    for model, multiplier in ATR_MODELS.items():
        config = config_for_atr(base_config, multiplier)
        trades = run_backtest(enriched, config)

        target = year_dir / model.lower()
        target.mkdir(parents=True, exist_ok=True)
        trades.to_csv(target / "trades.csv", index=False)

        summary = summarize(year, model, trades)
        distance = stop_distance_summary(year, model, trades)

        (target / "metrics.json").write_text(
            json.dumps(
                {
                    "performance": summary,
                    "stop_distance": distance,
                    "atr_period": 14,
                    "atr_multiplier": multiplier,
                },
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )

        summaries.append(summary)
        distance_rows.append(distance)
        family_rows.extend(setup_family_summary(year, model, trades))

        print(
            f"R5.3 {year} {model}: "
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
    pd.DataFrame(family_rows).to_csv(
        output / f"setup_family_summary_{year}.csv",
        index=False,
    )
    pd.DataFrame(distance_rows).to_csv(
        output / f"stop_distance_summary_{year}.csv",
        index=False,
    )

    print(f"Saved R5.3 summaries for {year} under {output}", flush=True)

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
        default=ROOT / "data/reports/R5_atr_stop",
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
