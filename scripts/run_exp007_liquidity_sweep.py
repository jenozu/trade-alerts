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

from liquidity_sweep_research import (
    analyze_liquidity_sweeps,
    enrich_trades_with_sweep_context,
    markdown_report,
    metrics_frame,
)


def parse_year_path(values):
    result = {}
    for raw in values:
        year, path = raw.split("=", 1)
        result[int(year)] = Path(path)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", action="append", required=True)
    parser.add_argument("--features", action="append", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--lookback", type=int, default=10)
    args = parser.parse_args()

    ledgers = parse_year_path(args.ledger)
    features = parse_year_path(args.features)

    if set(ledgers) != {2023, 2024, 2025}:
        raise SystemExit("EXP-007 requires 2023/2024/2025 ledgers")

    if set(features) != {2023, 2024, 2025}:
        raise SystemExit("EXP-007 requires 2023/2024/2025 features")

    enriched = {}

    for year in sorted(ledgers):
        ledger = pd.read_csv(ledgers[year])
        feature_df = pd.read_parquet(features[year])

        enriched[year] = enrich_trades_with_sweep_context(
            ledger,
            feature_df,
            lookback=args.lookback,
        )

    result = analyze_liquidity_sweeps(enriched)

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    md = out / "EXP-007-Liquidity-Sweep-Contribution.md"
    js = out / "exp007_liquidity_sweep_results.json"
    csv = out / "liquidity_sweep_metrics.csv"
    enriched_csv = out / "classified_sweep_trades.csv"

    md.write_text(
        markdown_report(
            result,
            {y: str(p) for y, p in ledgers.items()},
            {y: str(p) for y, p in features.items()},
        ),
        encoding="utf-8",
    )

    js.write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
            default=str,
        ),
        encoding="utf-8",
    )

    metrics_frame(result).to_csv(csv, index=False)

    pd.concat(
        [
            frame.assign(year=year)
            for year, frame in sorted(enriched.items())
        ],
        ignore_index=True,
    ).to_csv(enriched_csv, index=False)

    coverage = result["coverage"]

    print(f"EXP-007 complete: {md}")
    print(
        f"feature_match_rate="
        f"{100*coverage['match_rate']:.1f}% "
        f"({coverage['matched']}/{coverage['total_trades']})"
    )


if __name__ == "__main__":
    main()
