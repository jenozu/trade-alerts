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

from displacement_research import (
    analyze_displacement,
    enrich_displacement_context,
    markdown_report,
    metrics_frame,
)


def parse(values):
    out = {}
    for raw in values:
        year, path = raw.split("=", 1)
        out[int(year)] = Path(path)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", action="append", required=True)
    ap.add_argument("--features", action="append", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    ledgers = parse(args.ledger)
    features = parse(args.features)

    enriched = {}

    for year in (2023, 2024, 2025):
        enriched[year] = enrich_displacement_context(
            pd.read_csv(ledgers[year]),
            pd.read_parquet(features[year]),
        )

    result, classified = analyze_displacement(enriched)

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    md = out / "EXP-009-Displacement.md"
    js = out / "exp009_displacement_results.json"
    csv = out / "displacement_metrics.csv"
    trades = out / "classified_displacement_trades.csv"

    md.write_text(markdown_report(result), encoding="utf-8")
    js.write_text(
        json.dumps(result, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    metrics_frame(result).to_csv(csv, index=False)
    classified.to_csv(trades, index=False)

    print(f"EXP-009 complete: {md}")
    print(
        f"feature_match_rate="
        f"{result['coverage']['feature_matched']}/"
        f"{result['coverage']['total_trades']}"
    )


if __name__ == "__main__":
    main()
