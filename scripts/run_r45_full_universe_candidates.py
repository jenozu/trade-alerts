from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scorer import enrich_scores
from backtest import (
    run_backtest,
    calculate_backtest_metrics,
)
from score_candidate_models import CANDIDATE_WEIGHTS


def load_config(path: Path):
    return yaml.safe_load(path.read_text())


def model_config(base, weights):
    cfg = copy.deepcopy(base)

    cfg["scoring"]["positive_weights"] = {
        key: float(value)
        for key, value in weights.items()
    }

    return cfg


def safe_metrics(trades):
    if trades.empty:
        return {
            "trades": 0,
            "win_rate": None,
            "expectancy_points": None,
            "expectancy_r": None,
            "profit_factor": None,
            "net_points": 0.0,
        }

    return calculate_backtest_metrics(trades)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--features",
        action="append",
        required=True,
        help="YEAR=/path/to/features_scored.parquet",
    )

    parser.add_argument(
        "--config",
        default="config/strategy.yaml",
    )

    parser.add_argument(
        "--output-dir",
        required=True,
    )

    parser.add_argument(
        "--models",
        default="baseline,candidate_conservative,candidate_evidence_tilt,candidate_redundancy_reduced",
    )

    parser.add_argument(
        "--smoke-rows",
        type=int,
        default=0,
    )

    args = parser.parse_args()

    feature_paths = {}

    for raw in args.features:
        year, path = raw.split("=", 1)
        feature_paths[int(year)] = Path(path)

    years = sorted(feature_paths)

    if years != [2023, 2024, 2025]:
        raise SystemExit(
            f"Expected 2023/2024/2025, got {years}"
        )

    requested_models = [
        x.strip()
        for x in args.models.split(",")
        if x.strip()
    ]

    for model in requested_models:
        if model not in CANDIDATE_WEIGHTS:
            raise SystemExit(
                f"Unknown model: {model}"
            )

    base_config = load_config(
        Path(args.config)
    )

    out = Path(args.output_dir)
    out.mkdir(
        parents=True,
        exist_ok=True,
    )

    all_results = {}

    for year in years:
        path = feature_paths[year]

        print()
        print("=" * 90)
        print(f"YEAR {year}")
        print(path)
        print("=" * 90)

        features = pd.read_parquet(path)

        features["timestamp"] = pd.to_datetime(
            features["timestamp"],
            utc=True,
            errors="coerce",
        )

        features = features.sort_values(
            "timestamp"
        ).reset_index(drop=True)

        if args.smoke_rows > 0:
            features = features.tail(
                args.smoke_rows
            ).copy()

            print(
                f"SMOKE MODE: {len(features):,} rows"
            )

        all_results[str(year)] = {}

        for model in requested_models:
            print()
            print(
                f"--- {year} / {model} ---"
            )

            config = model_config(
                base_config,
                CANDIDATE_WEIGHTS[model],
            )

            scored = enrich_scores(
                features.copy(),
                config,
            )

            trades = run_backtest(
                scored,
                config,
            )

            metrics = safe_metrics(
                trades
            )

            model_dir = (
                out
                / str(year)
                / model
            )

            model_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            trades.to_csv(
                model_dir / "trades.csv",
                index=False,
            )

            (
                model_dir / "metrics.json"
            ).write_text(
                json.dumps(
                    metrics,
                    indent=2,
                    default=str,
                )
            )

            all_results[str(year)][model] = {
                "weights":
                    CANDIDATE_WEIGHTS[model],

                "metrics":
                    metrics,
            }

            print(
                "trades:",
                metrics.get("trades"),
            )

            print(
                "expectancy:",
                metrics.get(
                    "expectancy_points"
                ),
            )

            print(
                "PF:",
                metrics.get(
                    "profit_factor"
                ),
            )

    # Aggregate model performance across all years.
    aggregate = {}

    for model in requested_models:
        trade_frames = []

        for year in years:
            p = (
                out
                / str(year)
                / model
                / "trades.csv"
            )

            df = pd.read_csv(p)

            if not df.empty:
                df["research_year"] = year
                trade_frames.append(df)

        if trade_frames:
            combined = pd.concat(
                trade_frames,
                ignore_index=True,
            )

            aggregate_metrics = (
                calculate_backtest_metrics(
                    combined
                )
            )
        else:
            combined = pd.DataFrame()
            aggregate_metrics = {
                "trades": 0
            }

        aggregate[model] = (
            aggregate_metrics
        )

        combined.to_csv(
            out /
            f"{model}_all_years_trades.csv",
            index=False,
        )

    summary_rows = []

    for model, metrics in aggregate.items():
        summary_rows.append({
            "model": model,
            "trades":
                metrics.get("trades"),
            "win_rate":
                metrics.get("win_rate"),
            "expectancy_points":
                metrics.get(
                    "expectancy_points"
                ),
            "expectancy_r":
                metrics.get(
                    "expectancy_r"
                ),
            "profit_factor":
                metrics.get(
                    "profit_factor"
                ),
            "net_points":
                metrics.get(
                    "net_points"
                ),
            "tp1_hit_rate":
                metrics.get(
                    "tp1_hit_rate"
                ),
            "tp2_hit_rate":
                metrics.get(
                    "tp2_hit_rate"
                ),
            "tp3_hit_rate":
                metrics.get(
                    "tp3_hit_rate"
                ),
            "tp4_hit_rate":
                metrics.get(
                    "tp4_hit_rate"
                ),
            "stop_rate":
                metrics.get(
                    "stop_rate"
                ),
        })

    summary = pd.DataFrame(
        summary_rows
    )

    summary.to_csv(
        out / "model_summary.csv",
        index=False,
    )

    (
        out / "r45_results.json"
    ).write_text(
        json.dumps(
            {
                "years":
                    all_results,
                "aggregate":
                    aggregate,
            },
            indent=2,
            default=str,
        )
    )

    print()
    print("=" * 90)
    print("R4.5 SUMMARY")
    print("=" * 90)

    print(
        summary.to_string(
            index=False
        )
    )

    print()
    print("R4.5 complete")


if __name__ == "__main__":
    main()
