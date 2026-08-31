from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


DEFAULT_TRADES = Path("data/results/backtest/trades.csv")
DEFAULT_CONFIG = Path("config/strategy.yaml")
DEFAULT_OUTPUT = Path("data/results/backtest/exit_model_comparison.csv")


class ExitModelError(RuntimeError):
    """Raised when exit-model comparison cannot be completed safely."""


def load_strategy_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    if not isinstance(config, dict):
        raise ExitModelError("strategy.yaml did not produce a dictionary.")
    return config


def load_trades(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    trades = pd.read_csv(path)
    if trades.empty:
        raise ExitModelError("Trade file is empty; there is nothing to compare.")

    required = {
        "net_result_points",
        "net_result_r",
        "stop_distance_points",
        "tp1_hit",
        "tp2_hit",
        "tp3_hit",
        "tp4_hit",
    }
    missing = required - set(trades.columns)
    if missing:
        raise ExitModelError(
            f"Trade file is missing required columns: {sorted(missing)}"
        )
    return trades


def _boolean_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    normalized = series.astype(str).str.strip().str.lower()
    return normalized.isin({"true", "1", "yes", "y"})


def _profit_factor(results: pd.Series) -> float:
    winners = results.loc[results > 0]
    losers = results.loc[results < 0]
    gross_profit = float(winners.sum())
    gross_loss = abs(float(losers.sum()))
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def _summarize_model(
    *,
    model_name: str,
    target_points: float | None,
    results: pd.Series,
    stop_distances: pd.Series,
) -> dict[str, Any]:
    r_results = results / stop_distances.replace(0, np.nan)
    return {
        "model": model_name,
        "target_points": target_points,
        "trades": int(len(results)),
        "wins": int((results > 0).sum()),
        "losses": int((results < 0).sum()),
        "breakeven": int((results == 0).sum()),
        "win_rate": float((results > 0).mean()),
        "total_points": float(results.sum()),
        "expectancy_points": float(results.mean()),
        "expectancy_r": float(r_results.mean()) if r_results.notna().any() else None,
        "profit_factor": _profit_factor(results),
        "median_result_points": float(results.median()),
    }


def compare_exit_models(
    trades: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Compare full-exit TP1/TP2/TP3/TP4 models on the same trade signals.

    This does not change entries, stops, signal selection, scoring, or the market
    path used by the original backtest. A target model exits at its target when
    the corresponding milestone flag is true. If that target was never reached,
    the model keeps the original backtest exit result (stop, timeout, or end of
    data). Because the original backtest uses stop-first resolution on ambiguous
    same-bar stop/target candles, the milestone flags already preserve that
    conservative ordering.
    """
    take_profit = config.get("take_profit", {}).get("preferred_initial", {})
    backtest = config.get("backtest", {})
    slippage = backtest.get("slippage", {})

    target_points = {
        "tp1": float(take_profit.get("tp1_points", 25.0)),
        "tp2": float(take_profit.get("tp2_points", 50.0)),
        "tp3": float(take_profit.get("tp3_points", 75.0)),
        "tp4": float(take_profit.get("tp4_points", 100.0)),
    }

    exit_slippage = (
        float(slippage.get("points_per_exit", 0.25))
        if bool(slippage.get("enabled", True))
        else 0.0
    )

    baseline = pd.to_numeric(trades["net_result_points"], errors="raise")
    stop_distances = pd.to_numeric(trades["stop_distance_points"], errors="raise")

    records = [
        _summarize_model(
            model_name="current_baseline",
            target_points=None,
            results=baseline,
            stop_distances=stop_distances,
        )
    ]

    for target_name in ["tp1", "tp2", "tp3", "tp4"]:
        hit_column = f"{target_name}_hit"
        hits = _boolean_series(trades[hit_column])

        # Targets are defined from the slippage-adjusted entry price in the
        # existing backtester, so only adverse exit slippage must be deducted
        # from the target distance here.
        target_result = target_points[target_name] - exit_slippage
        model_results = baseline.copy()
        model_results.loc[hits] = target_result

        records.append(
            _summarize_model(
                model_name=f"full_exit_{target_name}",
                target_points=target_points[target_name],
                results=model_results,
                stop_distances=stop_distances,
            )
        )

    result = pd.DataFrame(records)

    # The current simulator exits fully at TP4 when TP4 is reached. Therefore
    # full_exit_tp4 should match current_baseline. Keep a diagnostic column so a
    # future code change cannot silently break this assumption.
    baseline_expectancy = float(
        result.loc[result["model"] == "current_baseline", "expectancy_points"].iloc[0]
    )
    result["expectancy_delta_vs_baseline"] = (
        result["expectancy_points"] - baseline_expectancy
    )

    return result


def save_results(result: pd.DataFrame, output_path: Path) -> tuple[Path, Path]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)

    json_path = output_path.with_suffix(".json")
    with json_path.open("w", encoding="utf-8") as file:
        json.dump(result.to_dict(orient="records"), file, indent=2, default=str)

    return output_path, json_path


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare fixed full-exit TP1/TP2/TP3/TP4 models using the same "
            "signals and stops from an existing backtest."
        )
    )
    parser.add_argument("--trades", type=Path, default=DEFAULT_TRADES)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    trades = load_trades(args.trades)
    config = load_strategy_config(args.config)
    result = compare_exit_models(trades, config)
    csv_path, json_path = save_results(result, args.output)

    print("\n============================================================")
    print("EXIT MODEL COMPARISON")
    print("============================================================")
    print(result.to_string(index=False))
    print("\nSaved:")
    print(f"  CSV:  {csv_path}")
    print(f"  JSON: {json_path}")


if __name__ == "__main__":
    main()
