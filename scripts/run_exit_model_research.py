from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIRECTORY = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SRC_DIRECTORY))

from analyze_exit_models import compare_exit_models, save_results  # noqa: E402
from backtest import (  # noqa: E402
    calculate_backtest_metrics,
    run_backtest,
    save_backtest_outputs,
)
from feature_cache import (  # noqa: E402
    FeatureCacheError,
    load_scored_cache,
    validate_feature_cache,
)


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise FeatureCacheError(f"Invalid YAML configuration: {path}")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run exit-model research from a certified scored feature cache. "
            "The expensive feature pipeline is not recomputed."
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
        default=str(PROJECT_ROOT / "data" / "results" / "exit_model_research"),
    )
    parser.add_argument(
        "--allow-code-mismatch",
        action="store_true",
        help=(
            "Skip feature-code manifest verification. Use only when the cached "
            "feature logic is intentionally being treated as frozen."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    cache_dir = Path(args.cache_dir)
    input_file = Path(args.input)
    strategy_config_path = Path(args.strategy_config)
    sessions_config_path = Path(args.sessions_config)
    output_dir = Path(args.output_dir)

    validation = validate_feature_cache(
        cache_dir,
        input_file=input_file,
        strategy_config=strategy_config_path,
        sessions_config=sessions_config_path,
        verify_feature_code=not args.allow_code_mismatch,
    )

    print("=== FEATURE CACHE VALIDATION ===")
    print(f"cache: {cache_dir}")
    print(f"valid: {validation.valid}")
    if validation.reasons:
        for reason in validation.reasons:
            print(f"  - {reason}")

    if not validation.valid:
        raise SystemExit(2)

    print()
    print("CACHE HIT")
    print(f"Loading {validation.rows:,} scored bars from:")
    print(validation.scored_path)

    dataframe = load_scored_cache(validation)
    strategy_config = load_yaml(strategy_config_path)

    print()
    print("=== REBUILD BASELINE TRADES FROM CACHE ===")
    trades = run_backtest(dataframe, strategy_config)
    if trades.empty:
        raise SystemExit("No trades were generated from the scored cache.")

    output_dir.mkdir(parents=True, exist_ok=True)
    baseline_dir = output_dir / "baseline"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    save_backtest_outputs(trades, baseline_dir)
    baseline_metrics = calculate_backtest_metrics(trades)

    print(f"Bars: {len(dataframe):,}")
    print(f"Trades: {len(trades):,}")
    print(f"Baseline expectancy: {baseline_metrics.get('expectancy_points')}")
    print(f"Baseline profit factor: {baseline_metrics.get('profit_factor')}")

    print()
    print("=== EXIT MODEL COMPARISON ===")
    comparison = compare_exit_models(trades, strategy_config)
    csv_path, json_path = save_results(
        comparison,
        output_dir / "exit_model_comparison.csv",
    )

    display_columns = [
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
        "expectancy_delta_vs_baseline",
    ]
    print(comparison[display_columns].to_string(index=False))

    summary = {
        "cache_directory": str(cache_dir),
        "scored_cache": str(validation.scored_path),
        "bars": int(len(dataframe)),
        "trades": int(len(trades)),
        "baseline_metrics": baseline_metrics,
        "comparison_csv": str(csv_path),
        "comparison_json": str(json_path),
        "models": comparison.to_dict(orient="records"),
        "note": (
            "This script compares the existing baseline with full-position exits "
            "at TP1/TP2/TP3/TP4 using the original trade signals and milestone "
            "flags. Path-dependent partial-exit and break-even-runner models "
            "require a separate bar-by-bar exit simulator and are intentionally "
            "not approximated here."
        ),
    }
    summary_path = output_dir / "research_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, default=str),
        encoding="utf-8",
    )

    print()
    print("Saved:")
    print(f"  baseline:   {baseline_dir}")
    print(f"  comparison: {csv_path}")
    print(f"  summary:    {summary_path}")
    print()
    print(
        "NOTE: partial exits and break-even runners are path-dependent and are "
        "not approximated by this script."
    )


if __name__ == "__main__":
    main()
