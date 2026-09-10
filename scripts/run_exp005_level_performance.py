from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from level_research import analyze_level_performance, enrich_trades_with_levels, markdown_report, metrics_frame


def parse_year_path(values: list[str]) -> dict[int, Path]:
    out: dict[int, Path] = {}
    for raw in values:
        if "=" not in raw:
            raise SystemExit(f"Expected YEAR=PATH, got: {raw}")
        year_s, path_s = raw.split("=", 1)
        out[int(year_s)] = Path(path_s)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Run EXP-005 level-specific performance research from existing artifacts")
    parser.add_argument("--ledger", action="append", required=True, help="YEAR=/path/to/trades.csv")
    parser.add_argument("--features", action="append", required=True, help="YEAR=/path/to/features_scored.parquet")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--recent-sweep-lookback", type=int, default=10)
    args = parser.parse_args()

    ledgers = parse_year_path(args.ledger)
    features = parse_year_path(args.features)
    if set(ledgers) != set(features):
        raise SystemExit("Ledger and feature years must match exactly")

    enriched: dict[int, pd.DataFrame] = {}
    for year in sorted(ledgers):
        ledger = pd.read_csv(ledgers[year])
        feature_df = pd.read_parquet(features[year])
        enriched[year] = enrich_trades_with_levels(ledger, feature_df, recent_sweep_lookback=args.recent_sweep_lookback)

    result = analyze_level_performance(enriched)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    md_path = out / "EXP-005-Important-Liquidity-Level.md"
    json_path = out / "exp005_level_results.json"
    csv_path = out / "level_metrics.csv"
    coverage_path = out / "classified_trades.csv"

    md_path.write_text(markdown_report(result, {y: str(p) for y,p in ledgers.items()}, {y: str(p) for y,p in features.items()}), encoding="utf-8")
    json_path.write_text(json.dumps(result, indent=2, sort_keys=True, default=str), encoding="utf-8")
    metrics_frame(result).to_csv(csv_path, index=False)
    pd.concat([f.assign(year=y) for y,f in sorted(enriched.items())], ignore_index=True).to_csv(coverage_path, index=False)

    print(f"EXP-005 complete: {md_path}")
    print(f"classification_rate={100*result['coverage']['classification_rate']:.1f}% ({result['coverage']['classified_trades']}/{result['coverage']['total_trades']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
