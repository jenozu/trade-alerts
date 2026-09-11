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

from htf_bias_research import analyze_htf_bias, enrich_trades_with_htf_bias, markdown_report, metrics_frame


def parse_year_path(values: list[str]) -> dict[int, Path]:
    out: dict[int, Path] = {}
    for raw in values:
        if "=" not in raw:
            raise SystemExit(f"Expected YEAR=PATH, got: {raw}")
        year_s, path_s = raw.split("=", 1)
        out[int(year_s)] = Path(path_s)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Run EXP-006 HTF-bias research from existing ledgers and scored features")
    parser.add_argument("--ledger", action="append", required=True, help="YEAR=/path/to/trades.csv")
    parser.add_argument("--features", action="append", required=True, help="YEAR=/path/to/features_scored.parquet")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    ledgers = parse_year_path(args.ledger)
    features = parse_year_path(args.features)
    if set(ledgers) != {2023, 2024, 2025} or set(features) != {2023, 2024, 2025}:
        raise SystemExit("EXP-006 requires exactly 2023, 2024, and 2025 ledger/feature paths")

    enriched: dict[int, pd.DataFrame] = {}
    for year in sorted(ledgers):
        ledger = pd.read_csv(ledgers[year])
        feature_df = pd.read_parquet(features[year])
        enriched[year] = enrich_trades_with_htf_bias(ledger, feature_df)

    result = analyze_htf_bias(enriched)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    md_path = out / "EXP-006-HTF-Bias.md"
    json_path = out / "exp006_htf_bias_results.json"
    csv_path = out / "htf_bias_metrics.csv"

    md_path.write_text(
        markdown_report(
            result,
            {y: str(p) for y, p in ledgers.items()},
            {y: str(p) for y, p in features.items()},
        ),
        encoding="utf-8",
    )
    json_path.write_text(json.dumps(result, indent=2, sort_keys=True, default=str), encoding="utf-8")
    metrics_frame(result).to_csv(csv_path, index=False)

    coverage = result["coverage"]
    print(f"EXP-006 complete: {md_path}")
    print(f"feature_match_rate={100*coverage['match_rate']:.1f}% ({coverage['feature_matched']}/{coverage['total_trades']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
