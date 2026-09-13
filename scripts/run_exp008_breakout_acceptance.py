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

from breakout_acceptance_research import (
    analyze_exp008,
    enrich_continuations,
    markdown_report,
    metrics_frame,
)


def parse(values):
    out = {}
    for raw in values:
        y, p = raw.split("=", 1)
        out[int(y)] = Path(p)
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
        enriched[year] = enrich_continuations(
            pd.read_csv(ledgers[year]),
            pd.read_parquet(features[year]),
        )

    result, classified = analyze_exp008(enriched)

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    md = out / "EXP-008-Breakout-Acceptance-Quality.md"
    js = out / "exp008_breakout_acceptance_results.json"
    csv = out / "breakout_acceptance_metrics.csv"
    trades = out / "classified_continuation_trades.csv"

    md.write_text(markdown_report(result), encoding="utf-8")
    js.write_text(
        json.dumps(result, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    metrics_frame(result).to_csv(csv, index=False)
    classified.to_csv(trades, index=False)

    print(f"EXP-008 complete: {md}")
    print(
        f"continuations={result['coverage']['continuation_trades']}, "
        f"matched={result['coverage']['feature_matched']}"
    )


if __name__ == "__main__":
    main()
