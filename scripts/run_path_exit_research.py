from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIRECTORY = PROJECT_ROOT / "src"
if str(SRC_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SRC_DIRECTORY))

from backtest import run_backtest  # noqa: E402
from feature_cache import load_scored_cache, validate_feature_cache  # noqa: E402
from path_exit_simulator import compare_path_exit_models  # noqa: E402


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise RuntimeError(f"Invalid YAML configuration: {path}")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare path-aware partial and break-even exit models on the same "
            "baseline trade entries using a certified scored feature cache."
        )
    )
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument(
        "--strategy-config",
        default=str(PROJECT_ROOT / "config" / "strategy.yaml"),
    )
    parser.add_argument(
        "--sessions-config",
        default=str(PROJECT_ROOT / "config" / "sessions.yaml"),
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "data" / "results" / "path_exit_research"),
    )
    parser.add_argument("--allow-code-mismatch", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cache_dir = Path(args.cache_dir)
    input_file = Path(args.input)
    strategy_path = Path(args.strategy_config)
    sessions_path = Path(args.sessions_config)
    output_dir = Path(args.output_dir)

    validation = validate_feature_cache(
        cache_dir,
        input_file=input_file,
        strategy_config=strategy_path,
        sessions_config=sessions_path,
        verify_feature_code=not args.allow_code_mismatch,
    )

    print("=== FEATURE CACHE VALIDATION ===")
    print(f"cache: {cache_dir}")
    print(f"valid: {validation.valid}")
    for reason in validation.reasons:
        print(f"  - {reason}")
    if not validation.valid:
        raise SystemExit(2)

    print("\nCACHE HIT")
    print(f"Loading {validation.rows:,} scored bars from:")
    print(validation.scored_path)
    bars = load_scored_cache(validation)
    bars = bars.sort_values("timestamp").reset_index(drop=True)

    config = load_yaml(strategy_path)
    baseline_trades = run_backtest(bars, config)
    if baseline_trades.empty:
        raise SystemExit("No baseline trades were generated.")

    backtest_cfg = config.get("backtest", {})
    slippage_cfg = backtest_cfg.get("slippage", {})
    exit_slippage = (
        float(slippage_cfg.get("points_per_exit", 0.25))
        if bool(slippage_cfg.get("enabled", True))
        else 0.0
    )
    stop_first = (
        str(backtest_cfg.get("same_bar_stop_and_target_behavior", "stop_first"))
        == "stop_first"
    )

    print("\n=== PATH-AWARE EXIT MODEL RESEARCH ===")
    print(f"Bars: {len(bars):,}")
    print(f"Baseline trades: {len(baseline_trades):,}")
    print("Signal set: fixed to baseline entries for clean exit-management isolation")

    summary, detail = compare_path_exit_models(
        bars,
        baseline_trades,
        exit_slippage_points=exit_slippage,
        stop_first=stop_first,
    )

    # Hard certification: the path simulator's baseline must exactly reproduce
    # the existing simulator's per-trade results before alternative models are
    # considered trustworthy.
    baseline_path = detail.loc[detail["model"] == "current_baseline"].sort_values("trade_id")
    baseline_original = baseline_trades.sort_values("trade_id")
    if len(baseline_path) != len(baseline_original):
        raise SystemExit("Baseline certification failed: trade counts differ.")

    diffs = (
        baseline_path["net_result_points"].to_numpy()
        - baseline_original["net_result_points"].to_numpy()
    )
    max_abs_diff = float(abs(diffs).max()) if len(diffs) else 0.0
    if max_abs_diff > 1e-9:
        raise SystemExit(
            "Baseline certification failed: path-aware results do not reproduce "
            f"the existing backtester (max diff {max_abs_diff})."
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    baseline_trades.to_csv(output_dir / "baseline_trades.csv", index=False)
    summary.to_csv(output_dir / "exit_model_summary.csv", index=False)
    detail.to_csv(output_dir / "exit_model_trade_detail.csv", index=False)

    payload = {
        "cache_dir": str(cache_dir),
        "bars": int(len(bars)),
        "baseline_trades": int(len(baseline_trades)),
        "baseline_certified": True,
        "baseline_max_abs_point_difference": max_abs_diff,
        "models": summary.to_dict(orient="records"),
    }
    (output_dir / "research_summary.json").write_text(
        json.dumps(payload, indent=2, default=str),
        encoding="utf-8",
    )

    columns = [
        "model",
        "trades",
        "wins",
        "losses",
        "breakeven",
        "win_rate",
        "total_points",
        "expectancy_points",
        "expectancy_r",
        "profit_factor",
        "max_drawdown_points",
        "average_winner_points",
        "average_loser_points",
        "longest_losing_streak",
        "expectancy_delta_vs_baseline",
    ]
    print("\nBASELINE CERTIFICATION: PASS")
    print(f"max per-trade point difference: {max_abs_diff}")
    print("\n=== COMPARISON ===")
    print(summary[columns].to_string(index=False))
    print("\nSaved:")
    print(f"  {output_dir / 'exit_model_summary.csv'}")
    print(f"  {output_dir / 'exit_model_trade_detail.csv'}")
    print(f"  {output_dir / 'research_summary.json'}")
    print(
        "\nNOTE: exit models intentionally reuse the same baseline entries so this "
        "isolates trade-management effects. Earlier exits do not introduce new "
        "signals that were blocked by the baseline one-open-trade rule."
    )


if __name__ == "__main__":
    main()
