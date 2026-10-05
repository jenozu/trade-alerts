from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIRECTORY = PROJECT_ROOT / "src"
if str(SRC_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SRC_DIRECTORY))

from experiment_identity import build_input_lock, verify_input_lock, write_input_lock  # noqa: E402
from backtest import (  # noqa: E402
    CONFIRMED_EXECUTION_MODEL,
    LEGACY_EXECUTION_MODEL,
    MARKET_EXECUTION_MODEL,
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
        description="Run a backtest from a certified scored feature cache."
    )
    parser.add_argument("--execution-model", choices=[LEGACY_EXECUTION_MODEL, CONFIRMED_EXECUTION_MODEL, MARKET_EXECUTION_MODEL],
                        help="Override execution semantics; confirmed mode requires production sequence/event columns")
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
        default=str(PROJECT_ROOT / "data" / "results" / "cached_backtest"),
    )
    parser.add_argument(
        "--allow-code-mismatch",
        action="store_true",
        help=(
            "Skip feature-code manifest verification. Intended only when the "
            "feature-generating code is known to be unchanged in behavior."
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
    if args.execution_model is not None:
        strategy_config.setdefault("backtest", {})["execution_model"] = args.execution_model

    lock = build_input_lock(
        experiment_id="CACHED-BACKTEST", root=PROJECT_ROOT,
        files={"scored_cache": validation.scored_path.resolve(),
               "cache_metadata": validation.metadata_path.resolve(),
               "source_data": input_file.resolve(),
               "strategy": strategy_config_path.resolve(),
               "sessions": sessions_config_path.resolve(),
               "research_policy": PROJECT_ROOT / "config/research_policy.yaml",
               "dependencies": PROJECT_ROOT / "requirements.txt"},
        years=sorted(set(dataframe["timestamp"].dt.year)),
        contracts=dataframe["contract"].dropna().astype(str).unique().tolist()
                  if "contract" in dataframe else [],
        counts={"bars": len(dataframe), "candidates": int(sum(
            dataframe[column].fillna(False).astype(bool).sum()
            for column in ("long_candidate", "short_candidate") if column in dataframe)),
            "trades": None},
        settings={"execution": {"backtest": strategy_config.get("backtest", {}),
                                "stop_loss": strategy_config.get("stop_loss", {}),
                                "take_profit": strategy_config.get("take_profit", {}),
                                "trade_management": strategy_config.get("trade_management", {}),
                                "allow_code_mismatch": args.allow_code_mismatch},
                  "cost": strategy_config.get("backtest", {}).get("commission", {}),
                  "slippage": strategy_config.get("backtest", {}).get("slippage", {})},
        unavailable={"contracts": "cache has no contract column"} if "contract" not in dataframe else {},
    )
    # Lock before simulation; refuse reuse of an old output identity.
    write_input_lock(output_dir / "EXPERIMENT_INPUT_LOCK.json", lock)
    print()
    print("=== CACHED BACKTEST ===")
    trades = run_backtest(dataframe, strategy_config)
    verify_input_lock(lock, root=PROJECT_ROOT)
    output_dir.mkdir(parents=True, exist_ok=True)
    if strategy_config.get("backtest", {}).get("execution_model") == MARKET_EXECUTION_MODEL:
        (output_dir / "execution_decisions.json").write_text(
            json.dumps(trades.attrs["execution_decisions"], indent=2, allow_nan=False) + "\n")

    if trades.empty:
        trades.to_csv(output_dir / "trades.csv", index=False)
        metrics = {"trades": 0}
    else:
        metrics = calculate_backtest_metrics(trades)
        save_backtest_outputs(trades, output_dir)

    summary = {
        "input_identity_sha256": lock["input_identity_sha256"],
        "cache_directory": str(cache_dir),
        "scored_cache": str(validation.scored_path),
        "bars": int(len(dataframe)),
        "trades": int(len(trades)),
        "metrics": metrics,
    }
    (output_dir / "cached_backtest_summary.json").write_text(
        json.dumps(summary, indent=2, default=str),
        encoding="utf-8",
    )

    print(f"Bars: {len(dataframe):,}")
    print(f"Trades: {len(trades):,}")
    if trades.empty:
        print("No trades generated.")
    else:
        print(f"Win rate: {metrics.get('win_rate')}")
        print(f"Expectancy points: {metrics.get('expectancy_points')}")
        print(f"Expectancy R: {metrics.get('expectancy_r')}")
        print(f"Profit factor: {metrics.get('profit_factor')}")
    print(f"Outputs: {output_dir}")


if __name__ == "__main__":
    main()
